const mongoose = require("mongoose");
const path = require("path");
const dotenv = require("dotenv");

// Load environment variables from the src directory
dotenv.config({ path: path.join(__dirname, '../.env') });

const connectDB = async () => {
  try {
    if (!process.env.MONGO_URI) {
      throw new Error('MONGO_URI environment variable is not defined');
    }
    
    await mongoose.connect(process.env.MONGO_URI);
    console.log("✅ MongoDB Atlas connected");
  } catch (err) {
    console.error("❌ MongoDB connection error:", err.message);
    process.exit(1);
  }
};

module.exports = connectDB;
