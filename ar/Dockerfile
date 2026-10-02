FROM node:22-alpine AS build

WORKDIR /ar

COPY package*.json ./

RUN npm ci

COPY . .

# VITE_API_BASE_URL por defecto '' (mismo origen: /api en prod)
RUN npm run build


FROM nginx:alpine

COPY ar-nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /ar/dist /usr/share/nginx/html/ar/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
