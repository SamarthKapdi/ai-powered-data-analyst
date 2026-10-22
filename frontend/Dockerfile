# Stage 1: Build the React TypeScript application
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve using Nginx
FROM nginx:alpine

# Copy built artifacts from stage 1
COPY --from=build /app/dist /usr/share/nginx/html

# Custom nginx configuration for SPA routing & API proxying
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O - http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
