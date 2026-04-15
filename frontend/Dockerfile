FROM node:18

WORKDIR /app

COPY package*.json ./

# 🔥 TEMP FIX (since npm ci still failing)
RUN npm install

COPY . .

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]