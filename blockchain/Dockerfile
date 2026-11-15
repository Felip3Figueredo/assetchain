FROM node:22-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npx hardhat compile
EXPOSE 8545
HEALTHCHECK --interval=5s --timeout=3s --retries=20 \
  CMD node -e "fetch('http://127.0.0.1:8545',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'eth_chainId',params:[]})}).then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["npx", "hardhat", "node", "--hostname", "0.0.0.0"]
