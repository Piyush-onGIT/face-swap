const http = require("http");
const express = require("express");
const app = express();
const server = http.createServer(app);
const axios = require("axios");
const { createClient } = require("redis");
const { Blob } = require("buffer");
const Jimp = require("jimp");
const { MongoClient, ObjectId } = require("mongodb");
const { Server } = require("socket.io");
const Redis = require("ioredis");
const { createAdapter } = require("@socket.io/redis-adapter");
require('dotenv').config();

const redisHost = process.env.REDIS_HOST;
const redisPort = process.env.REDIS_PORT;
const mongoUri = process.env.MONGODB_URI;
const mongoName = process.env.MONGODB_NAME;

const mongoClient = new MongoClient(mongoUri);
const mongoDb = mongoClient.db(mongoName);
const collection = mongoDb.collection("aiphotobooths");
const redisClient = createClient({
  url: `redis://${redisHost}:${redisPort}`,
  database: 1,
});

const redis = new Redis(redisPort, redisHost);

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

// Configure the Redis adapter
const pubClient = new Redis(redisPort, redisHost);
const subClient = pubClient.duplicate();
io.adapter(createAdapter(pubClient, subClient)); // Use the adapter

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
    .quality(30)
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
      console.log(`Finding key ${channel}_whatsapp`);
      const phone = await redisClient.get(`${channel}_whatsapp`);
      console.log(phone);
      if (phone) {
        const messageToSend = `Exciting news! Your AI-generated image is ready to be shared. Here's the image for you: https://aibooth-result.vercel.app/${channel}. Can't wait for you to see it!`;
        await axios.post("https://api.gokapturehub.com/whatsapp/sendText", {
          phone: phone,
          message: messageToSend,
        });
      }
      resolve();
    } catch (error) {
      console.log("Error while sending image on whatsapp");
      reject(error);
    }
  });
}

async function sendEmail(channel, imageUrl) {
  return new Promise(async (resolve, reject) => {
    try {
      const email = await redisClient.get(`${channel}_email`);
      const eventId = await redisClient.get(`${channel}_email_data`);

      if (!email) return resolve("No email found");

      console.log(`Mailing to: ${email}`);

      const response = await axios.get(imageUrl, {
        responseType: "arraybuffer",
      });

      const urlParts = imageUrl.split("/");
      const imageName = urlParts[urlParts.length - 1];

      const imageBlob = new Blob([response.data]);
      const imageFile = new File([imageBlob], imageName, {
        type: "image/jpeg",
      });

      const eventName = (
        await collection.findOne({
          _id: new ObjectId(eventId),
        })
      ).name;

      const mailBody = `Here's your fantastic AI-generated photo from our photobooth! Enjoy the memories captured in this unique creation at ${
        eventName ?? "our event"
      }. Please find your image attached with this email`;

      const formData = new FormData();
      formData.append("to", email);
      formData.append("files", imageFile);
      formData.append(
        "subject",
        `GoKapture: ${eventName ?? "Generated image"}`
      );
      formData.append("body", mailBody);
      formData.append("imageUrl", imageUrl);
      formData.append("eventId", eventId);

      await axios.post(
        "https://api.gokapturehub.com/email/sendEmailWithAttachements",
        formData
      );
      resolve(`Email sent to ${email}`);
    } catch (error) {
      reject(error);
    }
  });
}

redis.on("message", async (channel, message) => {
  socketChannel = message.split(":")[0];
  socketMsg = message.split(":").slice(1).join(":");
  io.emit(socketChannel, socketMsg);
  console.log(`Emitted ${socketMsg}`);

  sendEmail(socketChannel, socketMsg)
    .then((data) => {
      console.log(data);
      console.log(`Async processing completed for message from ${channel}`);
    })
    .catch((error) => {
      console.error(`Error sending iamge from ${channel}:`, error.message);
    });

  console.log(`Received ${message} from ${channel} and sent it`);
});

io.on("connect", (socket) => {
  console.log("a user connected");
  socket.on('send',(socketChannel, socketMsg)=>{
    io.emit(socketChannel, socketMsg);
  })
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

server.listen(5001, () => console.log(`HTTP Server started at PORT:5001`));
