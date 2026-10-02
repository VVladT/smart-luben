import pytest
from httpx import AsyncClient


class TestProductos:
    @pytest.mark.asyncio
    async def test_crear_producto(self, client: AsyncClient):
        response = await client.post("/api/productos", json={
            "nombre": "Test Producto",
            "categoria": "Test",
            "imagen_url": "https://example.com/img.jpg"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "Test Producto"
        assert data["categoria"] == "Test"
        assert data["activo"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_crear_producto_duplicado(self, client: AsyncClient):
        await client.post("/api/productos", json={
            "nombre": "Duplicado",
            "categoria": "Test"
        })
        response = await client.post("/api/productos", json={
            "nombre": "Duplicado",
            "categoria": "Test"
        })
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_listar_productos(self, client: AsyncClient):
        await client.post("/api/productos", json={"nombre": "Prod 1", "categoria": "Cat1"})
        await client.post("/api/productos", json={"nombre": "Prod 2", "categoria": "Cat2", "activo": False})
        
        response = await client.get("/api/productos")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        
        response = await client.get("/api/productos?activo=true")
        assert response.status_code == 200
        data = response.json()
        assert all(p["activo"] for p in data)

    @pytest.mark.asyncio
    async def test_obtener_producto(self, client: AsyncClient):
        create_resp = await client.post("/api/productos", json={"nombre": "Get Test", "categoria": "Test"})
        producto_id = create_resp.json()["id"]
        
        response = await client.get(f"/api/productos/{producto_id}")
        assert response.status_code == 200
        assert response.json()["id"] == producto_id

    @pytest.mark.asyncio
    async def test_obtener_producto_no_existe(self, client: AsyncClient):
        response = await client.get("/api/productos/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_actualizar_producto(self, client: AsyncClient):
        create_resp = await client.post("/api/productos", json={"nombre": "Original", "categoria": "Test"})
        producto_id = create_resp.json()["id"]

        response = await client.put(f"/api/productos/{producto_id}", json={
            "nombre": "Actualizado",
            "categoria": "Nueva Cat"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "Actualizado"
        assert data["categoria"] == "Nueva Cat"

    @pytest.mark.asyncio
    async def test_actualizar_modelo_bump_version(self, client: AsyncClient):
        create_resp = await client.post("/api/productos", json={"nombre": "Con Modelo", "categoria": "Test"})
        producto_id = create_resp.json()["id"]
        assert create_resp.json()["version"] == "v1.0.0"

        response = await client.put(f"/api/productos/{producto_id}", json={
            "modelo_url": "http://localhost:9000/modelos/nuevo.glb",
            "scale": 1.5,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["modelo_url"] == "http://localhost:9000/modelos/nuevo.glb"
        assert data["scale"] == 1.5
        assert data["version"] == "v1.0.1"

        # Sin cambio de modelo ni transforms no bumpea
        response = await client.put(f"/api/productos/{producto_id}", json={"categoria": "Otra"})
        assert response.json()["version"] == "v1.0.1"

    @pytest.mark.asyncio
    async def test_actualizar_scale_bump_version(self, client: AsyncClient):
        create_resp = await client.post("/api/productos", json={"nombre": "Scale P", "categoria": "Test"})
        producto_id = create_resp.json()["id"]
        assert create_resp.json()["version"] == "v1.0.0"

        response = await client.put(f"/api/productos/{producto_id}", json={"scale": 2.5})
        assert response.status_code == 200
        assert response.json()["scale"] == 2.5
        assert response.json()["version"] == "v1.0.1"

    @pytest.mark.asyncio
    async def test_presign_validaciones(self, client: AsyncClient):
        # Tipo inválido
        response = await client.post("/api/uploads/presign", json={
            "tipo": "exe", "filename": "x.exe", "content_type": "application/x-msdownload"
        })
        assert response.status_code == 400

        # Extensión inválida para modelo
        response = await client.post("/api/uploads/presign", json={
            "tipo": "modelo", "filename": "x.obj", "content_type": "application/octet-stream"
        })
        assert response.status_code == 400

        # Tamaño excedido
        response = await client.post("/api/uploads/presign", json={
            "tipo": "imagen", "filename": "x.png", "content_type": "image/png",
            "size": 100 * 1024 * 1024,
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_sync_changes(self, client: AsyncClient):
        create_resp = await client.post("/api/productos", json={"nombre": "Sync P", "categoria": "Test"})
        producto_id = create_resp.json()["id"]

        # Sin versiones conocidas: todo es cambio
        response = await client.post("/api/sync/changes", json={"versions": {}, "assignments": {}})
        assert response.status_code == 200
        assert any(c["type"] == "producto_update" and c["productoId"] == producto_id
                   for c in response.json()["changes"])

        # Con versión al día y sin espacios: sin cambios de ese producto
        response = await client.post("/api/sync/changes", json={
            "versions": {str(producto_id): "v1.0.0"}, "assignments": {}
        })
        assert response.status_code == 200
        assert not any(c.get("productoId") == producto_id and c["type"] == "producto_update"
                       for c in response.json()["changes"])

    @pytest.mark.asyncio
    async def test_sync_detecta_cambio_estado(self, client: AsyncClient, sample_producto, sample_espacio):
        # Planificar (sigue libre) y luego ocupar: el sync debe reportar el estado
        await client.post(f"/api/espacios/{sample_espacio.id}/planificar", json={
            "producto_id": sample_producto.id
        })
        await client.post(f"/api/espacios/{sample_espacio.id}/reponer", json={})

        response = await client.post("/api/sync/changes", json={
            "versions": {str(sample_producto.id): "v1.0.0"},
            "assignments": {sample_espacio.codigo: sample_producto.id},
            "estados": {sample_espacio.codigo: "libre"},
        })
        assert response.status_code == 200
        cambios = [c for c in response.json()["changes"] if c["type"] == "espacio_estado"]
        assert any(c["espacio_codigo"] == sample_espacio.codigo and c["estado"] == "ocupado"
                   for c in cambios)

        # Ya sincronizado: sin cambios
        response = await client.post("/api/sync/changes", json={
            "versions": {str(sample_producto.id): "v1.0.0"},
            "assignments": {sample_espacio.codigo: sample_producto.id},
            "estados": {sample_espacio.codigo: "ocupado"},
        })
        assert response.json()["changes"] == []

    @pytest.mark.asyncio
    async def test_eliminar_producto_soft(self, client: AsyncClient):
        create_resp = await client.post("/api/productos", json={"nombre": "Para Eliminar", "categoria": "Test"})
        producto_id = create_resp.json()["id"]
        
        response = await client.delete(f"/api/productos/{producto_id}")
        assert response.status_code == 200
        assert response.json()["activo"] is False
        
        response = await client.get(f"/api/productos/{producto_id}")
        assert response.status_code == 200
        assert response.json()["activo"] is False


class TestEspacios:
    @pytest.mark.asyncio
    async def test_crear_espacio(self, client: AsyncClient):
        response = await client.post("/api/espacios", json={
            "codigo": "E99",
            "ubicacion": "Test Location"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["codigo"] == "E99"
        assert data["estado"] == "libre"

    @pytest.mark.asyncio
    async def test_listar_espacios(self, client: AsyncClient):
        await client.post("/api/espacios", json={"codigo": "E100", "ubicacion": "Loc 1"})
        await client.post("/api/espacios", json={"codigo": "E101", "ubicacion": "Loc 2"})
        
        response = await client.get("/api/espacios")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_eliminar_espacio_libre(self, client: AsyncClient):
        create_resp = await client.post("/api/espacios", json={"codigo": "E200", "ubicacion": "Para Eliminar"})
        espacio_id = create_resp.json()["id"]
        
        response = await client.delete(f"/api/espacios/{espacio_id}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_eliminar_espacio_ocupado_falla(self, client: AsyncClient, sample_producto, sample_espacio):
        from app.models import EstadoEspacio
        from app.database import get_db
        
        reponer_resp = await client.post(f"/api/espacios/{sample_espacio.id}/reponer", json={
            "producto_id": sample_producto.id
        })
        assert reponer_resp.status_code == 200
        
        response = await client.delete(f"/api/espacios/{sample_espacio.id}")
        assert response.status_code == 400


class TestMovimientos:
    @pytest.mark.asyncio
    async def test_reponer_espacio_libre(self, client: AsyncClient, sample_producto, sample_espacio):
        # Nuevo contrato: reponer usa el planificado (planificar primero)
        plan_resp = await client.post(f"/api/espacios/{sample_espacio.id}/planificar", json={
            "producto_id": sample_producto.id
        })
        assert plan_resp.status_code == 200
        assert plan_resp.json()["situacion"] == "pendiente"

        response = await client.post(f"/api/espacios/{sample_espacio.id}/reponer", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["tipo"] == "reposicion"
        assert data["espacio_id"] == sample_espacio.id
        assert data["producto_id"] == sample_producto.id

        espacio_resp = await client.get(f"/api/espacios/{sample_espacio.id}")
        assert espacio_resp.json()["estado"] == "ocupado"
        assert espacio_resp.json()["producto_actual_id"] == sample_producto.id
        assert espacio_resp.json()["situacion"] == "ocupado"

    @pytest.mark.asyncio
    async def test_reponer_sin_plan_marca_desconocido(self, client: AsyncClient, sample_espacio):
        response = await client.post(f"/api/espacios/{sample_espacio.id}/reponer", json={})
        assert response.status_code == 200
        assert response.json()["producto_id"] is None

        espacio_resp = await client.get(f"/api/espacios/{sample_espacio.id}")
        assert espacio_resp.json()["estado"] == "ocupado"
        assert espacio_resp.json()["situacion"] == "desconocido"

    @pytest.mark.asyncio
    async def test_planificar_y_cancelar_plan(self, client: AsyncClient, sample_producto, sample_espacio):
        plan_resp = await client.post(f"/api/espacios/{sample_espacio.id}/planificar", json={
            "producto_id": sample_producto.id
        })
        assert plan_resp.status_code == 200
        assert plan_resp.json()["situacion"] == "pendiente"

        cancel_resp = await client.delete(f"/api/espacios/{sample_espacio.id}/plan")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["situacion"] == "libre"
        assert cancel_resp.json()["producto_actual_id"] is None

    @pytest.mark.asyncio
    async def test_reponer_espacio_ocupado_falla(self, client: AsyncClient, sample_producto, sample_espacio):
        await client.post(f"/api/espacios/{sample_espacio.id}/reponer", json={
            "producto_id": sample_producto.id
        })
        
        response = await client.post(f"/api/espacios/{sample_espacio.id}/reponer", json={
            "producto_id": sample_producto.id
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_liberar_espacio_ocupado(self, client: AsyncClient, sample_producto, sample_espacio):
        await client.post(f"/api/espacios/{sample_espacio.id}/reponer", json={
            "producto_id": sample_producto.id
        })
        
        response = await client.post(f"/api/espacios/{sample_espacio.id}/liberar")
        assert response.status_code == 200
        data = response.json()
        assert data["tipo"] == "salida"
        
        espacio_resp = await client.get(f"/api/espacios/{sample_espacio.id}")
        assert espacio_resp.json()["estado"] == "libre"
        assert espacio_resp.json()["producto_actual_id"] is None

    @pytest.mark.asyncio
    async def test_liberar_espacio_libre_falla(self, client: AsyncClient, sample_espacio):
        response = await client.post(f"/api/espacios/{sample_espacio.id}/liberar")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_historial_movimientos_con_filtros(self, client: AsyncClient, sample_producto, sample_espacio):
        await client.post(f"/api/espacios/{sample_espacio.id}/reponer", json={"producto_id": sample_producto.id})
        await client.post(f"/api/espacios/{sample_espacio.id}/liberar")
        
        response = await client.get("/api/movimientos")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        
        response = await client.get(f"/api/movimientos?espacio_id={sample_espacio.id}")
        assert response.status_code == 200
        
        response = await client.get(f"/api/movimientos?tipo=reposicion")
        assert response.status_code == 200
        data = response.json()
        assert all(m["tipo"] == "reposicion" for m in data)
        
        response = await client.get(f"/api/movimientos/espacio/{sample_espacio.id}")
        assert response.status_code == 200
        data = response.json()
        assert all(m["espacio_id"] == sample_espacio.id for m in data)


class TestDashboard:
    @pytest.mark.asyncio
    async def test_resumen_dashboard(self, client: AsyncClient):
        response = await client.get("/api/dashboard/resumen")
        assert response.status_code == 200
        data = response.json()
        assert "total_espacios" in data
        assert "espacios_libres" in data
        assert "espacios_ocupados" in data
        assert "productos_activos" in data
        assert data["total_espacios"] == data["espacios_libres"] + data["espacios_ocupados"]


class TestContratoAR:
    """Contrato que consume /ar (falla el CI de backend si se rompe)."""

    @pytest.mark.asyncio
    async def test_productos_traen_campos_3d(self, client: AsyncClient):
        await client.post("/api/productos", json={"nombre": "AR P", "categoria": "Test"})
        response = await client.get("/api/productos")
        assert response.status_code == 200
        for p in response.json():
            for campo in ("modelo_url", "scale", "rotation_x", "rotation_y", "rotation_z", "version"):
                assert campo in p, f"falta {campo} para AR"

    @pytest.mark.asyncio
    async def test_espacios_traen_situacion(self, client: AsyncClient, sample_espacio):
        response = await client.get("/api/espacios")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        for e in data:
            assert e["situacion"] in ("libre", "pendiente", "ocupado", "desconocido")
            assert "producto_actual_id" in e

    @pytest.mark.asyncio
    async def test_sync_changes_forma(self, client: AsyncClient):
        response = await client.post("/api/sync/changes", json={"versions": {}, "assignments": {}, "estados": {}})
        assert response.status_code == 200
        assert "changes" in response.json()
        assert isinstance(response.json()["changes"], list)
