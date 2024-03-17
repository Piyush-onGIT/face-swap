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
      // const response = await axios.get(imageUrl, {
      //   responseType: "arraybuffer",
      // });
      // const base64Image = Buffer.from(response.data, "binary").toString(
      //   "base64"
      // );
      // const base64Compressed = await compressBase64(base64Image);
      console.log(`Finding key ${channel}_whatsapp`);
      const phone = await redisClient.get(`${channel}_whatsapp`);
      console.log(phone);
      if (phone) {
        const messageToSend =
          "Exciting news! Your AI-generated image is ready to be shared. Here's the image for you: https://aibooth-result.vercel.app/${channel}. Can't wait for you to see it!";
        await axios.post("https://api.gokapturehub.com/whatsapp/sendText", {
          phone: phone,
          message: messageToSend,
        });
        // await axios.post("https://api.gokapturehub.com/whatsapp/sendImage", {
        //   phone: phone,
        //   image: base64Compressed,
        //   caption:
        //     "Exciting news! Your AI-generated image is ready to be shared. Here's the image for you. Can't wait for you to see it!",
        // });
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
      console.log(`Finding key ${channel}_email`);
      const email = await redisClient.get(`${channel}_email`);
      console.log(email);

      const response = await axios.get(imageUrl, {
        responseType: "arraybuffer",
      });

      const urlParts = imageUrl.split("/");
      const imageName = urlParts[urlParts.length - 1];

      const imageBlob = new Blob([response.data]);
      const imageFile = new File([imageBlob], imageName, {
        type: "image/jpeg",
      });

      const formData = new FormData();
      formData.append("to", email);
      formData.append("files", imageFile);
      formData.append("subject", "Gokapture generated image");
      formData.append(
        "body",
        "Here's your fantastic AI-generated photo from our photobooth! Enjoy the memories captured in this unique creation."
      );

      await axios.post(
        "https://api.gokapturehub.com/email/sendEmailWithAttachements",
        formData
      );
      resolve();
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

  // const imageBlob = new Blob([response.data]);
  // const imageFile = new File([imageBlob], 'image.jpg', { type: 'image/jpeg' });

  // processMessage(socketChannel, socketMsg)
  //   .then(() => {
  //     console.log(`Async processing started for message from ${channel}`);
  //   })
  //   .catch((error) => {
  //     console.error(`Error sending iamge from ${channel}:`, error.message);
  //   });

  sendEmail(socketChannel, socketMsg)
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
