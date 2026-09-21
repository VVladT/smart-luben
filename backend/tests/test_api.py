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
        response = await client.post(f"/api/espacios/{sample_espacio.id}/reponer", json={
            "producto_id": sample_producto.id
        })
        assert response.status_code == 200
        data = response.json()
        assert data["tipo"] == "reposicion"
        assert data["espacio_id"] == sample_espacio.id
        assert data["producto_id"] == sample_producto.id
        
        espacio_resp = await client.get(f"/api/espacios/{sample_espacio.id}")
        assert espacio_resp.json()["estado"] == "ocupado"
        assert espacio_resp.json()["producto_actual_id"] == sample_producto.id

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
        
        response = await client.get(f"/api/espacios/{sample_espacio.id}/movimientos")
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