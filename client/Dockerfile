FROM node:22-bookworm-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392
WORKDIR /client
COPY client/package*.json ./
RUN npm ci
COPY client/tsconfig.json ./
COPY client/src ./src
RUN npm run build
USER node
ENTRYPOINT ["node","dist/index.js"]
