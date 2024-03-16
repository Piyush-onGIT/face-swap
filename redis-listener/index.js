const http = require("http");
const express = require("express");
const app = express();
const server = http.createServer(app);
const axios = require("axios");

const { Server } = require("socket.io");
const Redis = require("ioredis");

const redis = new Redis(6379, "redis");

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

redis.on("message", async (channel, message) => {
  socketChannel = message.split(":")[0];
  socketMsg = message.split(":").slice(1).join(":");
  io.emit(socketChannel, socketMsg);
  // io.emit("gallery", socketMsg);
  const phone = await redis.get(`${socketChannel}:whatsapp`);
  console.log(phone);

  if (phone) {
    await axios.post("http://whatsapp:8003/sendText", {
      chatId: `91${phone}@c.us`,
      text: socketMsg,
      session: "default",
    });
  }

  console.log(`Received ${message} from ${channel} and sent it`);
});

io.on("connect", (socket) => {
  console.log("a user connected");
  socket.on("disconnect", () => {
    console.log("user disconnected");
  });
});

app.get("/", (req, res) => {
  res.send("<h1>Hello world</h1>");
});

server.listen(5001, () => console.log(`HTTP Server started at PORT:${5001}`));
