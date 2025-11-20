const dotenv = require('dotenv');
const path = require('path');
dotenv.config({ path: path.join(__dirname, '../.env') });
const mongoose = require('mongoose');
const connectDB = require("./config/db");
// console.log('Environment Variables:', process.env);
const app = require('./app');

const PORT = process.env.NODE_PORT || 5000;

process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception:', err);
  console.error('Shutting down the server due to uncaught exception...');
  // Optionally, you can exit the process
  process.exit(1); // Exit with failure code
});


// Connect to database
connectDB();

// Start server
const server = app.listen(PORT, () => {
    console.log(`🚀 Node server running on http://localhost:${PORT}`);
});

process.on('unhandledRejection', (err) => {
  console.error('Unhandled Rejection:', err);
  console.error('Shutting down the server due to unhandled rejection...');
  // Optionally, you can exit the process
  server.close(() => {
    console.error('Server closed due to unhandled rejection');
    process.exit(1); // Exit with failure code
  });
});

