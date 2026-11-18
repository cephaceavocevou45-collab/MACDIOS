FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_URL=
ENV VITE_API_URL=${VITE_API_URL}
ARG VITE_SENTRY_DSN=
ENV VITE_SENTRY_DSN=${VITE_SENTRY_DSN}
ARG APP_RELEASE_SHA=unknown
ENV APP_RELEASE_SHA=${APP_RELEASE_SHA}
RUN npm run build

FROM nginx:alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/ /usr/share/nginx/html/
EXPOSE 80
