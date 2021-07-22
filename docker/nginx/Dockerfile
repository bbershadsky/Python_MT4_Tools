
# The first stage
# Build React static files
FROM node:16.3.0-alpine as build

WORKDIR /app/frontend
COPY ./frontend/package.json ./
COPY ./frontend/yarn.lock ./
COPY ./frontend/ ./
RUN yarn add node-sass sass-loader
RUN yarn run build

# The second stage
# Copy React static files and start nginx
FROM nginx:stable-alpine
COPY --from=build /app/frontend/build /usr/share/nginx/html
CMD ["nginx", "-g", "daemon off;"]
