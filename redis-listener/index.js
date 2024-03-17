const http = require("http");
const express = require("express");
const app = express();
const server = http.createServer(app);
const axios = require("axios");
const { createClient } = require("redis");
const { Blob } = require("buffer");

const redisClient = createClient({ url: "redis://redis:6379" });

const { Server } = require("socket.io");
const Redis = require("ioredis");

const redis = new Redis(6379, "redis");

const connectRedis = async () => {
  await redisClient.connect();
};

const io = new Server({
  cors: {
    allowedHeaders: ["*"],
    origin: "*",
    methods: ["*"],
  },
});

io.attach(server);

redis.subscribe("task_completed", (err, count) => {
  if (err) {
    console.error("Failed to subscribe: %s", err.message);
  } else {
    console.log(
      `Subscribed successfully! This client is currently subscribed to "task_completed"`
    );
  }
});

async function processMessage(channel, imageUrl) {
  try {
    const response = await axios.get(imageUrl, {
      responseType: "arraybuffer",
    });
    const base64Image = Buffer.from(response.data, "binary").toString("base64");
    console.log(`Finding key ${channel}_whatsapp`);
    const phone = await redisClient.get(`${channel}_whatsapp`);
    console.log(phone);

    console.log(`${phone}:phone`);
    if (phone) {
      await axios.post("http://api-prod:8000/sendImage", {
        phone: phone,
        image: base64Image,
      });
    }
  } catch (error) {
    console.log("Error while sending image on whatsapp");
  }
}

redis.on("message", async (channel, message) => {
  socketChannel = message.split(":")[0];
  socketMsg = message.split(":").slice(1).join(":");
  io.emit(socketChannel, socketMsg);

  // const imageBlob = new Blob([response.data]);
  // const imageFile = new File([imageBlob], 'image.jpg', { type: 'image/jpeg' });

  await processMessage(socketChannel, socketMsg);

  console.log(`Received ${message} from ${channel} and sent it`);
});

io.on("connect", (socket) => {
  console.log("a user connected");
  socket.on("disconnect", () => {
    console.log("user disconnected");
  });
});

connectRedis();
app.get("/", (req, res) => {
  res.send("<h1>Hello world</h1>");
});

server.listen(5001, () => console.log(`HTTP Server started at PORT:${5001}`));
