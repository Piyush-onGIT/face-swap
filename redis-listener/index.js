const http = require("http");
const { Server } = require("socket.io");
const Redis = require("ioredis");

const httpServer = http.createServer();

const redis = new Redis(6379, "redis");
redis.set("mykey", "value");

const io = new Server({
  cors: {
    allowedHeaders: ["*"],
    origin: "*",
    methods: ["*"],
  },
});

io.attach(httpServer);

redis.subscribe("task_completed", (err, count) => {
  if (err) {
    console.error("Failed to subscribe: %s", err.message);
  } else {
    console.log(
      `Subscribed successfully! This client is currently subscribed to "task_completed"`
    );
  }
});

redis.on("message", (channel, message) => {
  socketChannel = message.split(":")[0];
  socketMsg = message.split(":").slice(1).join(":");
  io.emit(socketChannel, socketMsg);
  console.log(`Received ${message} from ${channel}`);
});

// io.on("connection", (socket) => {
//   console.log("a user connected");
//   // io.emit("taskId", "hi");
//   socket.on("disconnect", () => {
//     console.log("user disconnected");
//   });
// });

httpServer.listen(5001, () =>
  console.log(`HTTP Server started at PORT:${5001}`)
);
