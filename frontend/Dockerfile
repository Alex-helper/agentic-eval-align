FROM node:22-alpine
WORKDIR /app
COPY frontend/package.json ./
RUN npm install
COPY frontend ./
ENV VITE_API_BASE=http://localhost:8000
CMD ["npm", "run", "dev"]
