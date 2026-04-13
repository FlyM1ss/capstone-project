FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

# Dev server: reads NEXT_PUBLIC_* env vars at startup (fine for dev/demo).
# For production, replace with: RUN npm run build && CMD ["npm", "start"]
CMD ["npm", "run", "dev"]
