FROM node:22-alpine AS build

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:22-alpine

WORKDIR /app
COPY --from=build /app/dist ./dist
RUN npm install -g serve

EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:3000 || exit 1

CMD ["serve", "-s", "dist", "-l", "3000"]
