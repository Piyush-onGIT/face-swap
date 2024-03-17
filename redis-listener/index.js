const http = require("http");
const express = require("express");
const app = express();
const server = http.createServer(app);
const axios = require("axios");
const { createClient } = require("redis");
const { Blob } = require("buffer");
const Jimp = require("jimp");

const redisClient = createClient({ url: "redis://redis:6379", database: 0 });

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

const compressBase64 = async (base64) => {
  const bufferImageData = Buffer.from(base64, "base64");
  const image = await Jimp.read(bufferImageData);
  const compressedImageData = await image
    .quality(80)
    .getBufferAsync(Jimp.MIME_JPEG);
  const compressedBase64ImageData = compressedImageData.toString("base64");

  const actualSizeKB = (Buffer.byteLength(base64, "base64") / 1024).toFixed(2);
  const compressedSizeKB = (
    Buffer.byteLength(compressedBase64ImageData, "base64") / 1024
  ).toFixed(2);
  console.log("Actual size: ", actualSizeKB);
  console.log("Compressed size: ", compressedSizeKB);

  return compressedBase64ImageData;
};

async function processMessage(channel, imageUrl) {
  return new Promise(async (resolve, reject) => {
    try {
      const response = await axios.get(imageUrl, {
        responseType: "arraybuffer",
      });
      const base64Image = Buffer.from(response.data, "binary").toString(
        "base64"
      );
      const base64Compressed = await compressBase64(base64Image);

      console.log(`Finding key ${channel}_whatsapp`);
      const phone = await redisClient.get(`${channel}_whatsapp`);
      console.log(phone);

      console.log(`${phone}:phone`);
      if (phone) {
        await axios.post("http://api-prod:8000/sendImage", {
          phone: phone,
          image: base64Compressed,
        });
      }
      resolve();
    } catch (error) {
      console.log("Error while sending image on whatsapp");
      reject(error);
    }
  });
}

redis.on("message", async (channel, message) => {
  socketChannel = message.split(":")[0];
  socketMsg = message.split(":").slice(1).join(":");
  io.emit(socketChannel, socketMsg);
  console.log(`Emitted ${socketMsg}`);

  // const imageBlob = new Blob([response.data]);
  // const imageFile = new File([imageBlob], 'image.jpg', { type: 'image/jpeg' });

  processMessage(socketChannel, socketMsg)
    .then(() => {
      console.log(`Async processing started for message from ${channel}`);
    })
    .catch((error) => {
      console.error(`Error sending iamge from ${channel}:`, error.message);
    });

  console.log(`Received ${message} from ${channel} and sent it`);
});

io.on("connect", (socket) => {
  console.log("a user connected");
  socket.on("disconnect", () => {
    console.log("user disconnected");
  });
});

connectRedis()
  .then(() => console.log("Redis client connected"))
  .catch((err) => console.log(`Error connecting redis client ${err}`));
app.get("/", (req, res) => {
  res.send("<h1>Hello world</h1>");
});

server.listen(5001, () => console.log(`HTTP Server started at PORT:${5001}`));
