FROM node:24-alpine@sha256:a0b9bf06e4e6193cf7a0f58816cc935ff8c2a908f81e6f1a95432d679c54fbfd AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG DOCS_SITE=https://calidad.upeu.edu.pe
ARG DOCS_BASE=/manual
RUN DOCS_SITE="$DOCS_SITE" DOCS_BASE="$DOCS_BASE" npm run build

FROM nginxinc/nginx-unprivileged:1.28-alpine@sha256:7377697a821c131a924a7105fafbe7414db4e9fcc77a6f08f776f33f141ec3f8
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html/manual
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/manual/ || exit 1
