const express = require('express');
const morgan = require('morgan');
const fs = require('fs');
const path = require('path');
const helmet = require('helmet');
const dotenv = require('dotenv');
const userRouter = require('./routes/userRouter');
const fastapiRouter = require('./routes/fastapiRouter');
// const reservationRouter = require('./routes/reservationRouter');
const AppError = require('./utils/appError');
const globalErrorHandler = require('./controllers/errorController');
const cors = require('cors');   // <-- add this

const app = express();
dotenv.config(); // <-- must be FIRST before anything else

// 1) CORS — MUST be at the top
app.use(cors({
  origin: process.env.ALLOWED_ORIGIN || "http://localhost:3000",
  credentials: true,
}));

// Allow preflight requests for all routes
// app.options("*", cors());

// 1) Set security HTTP headers
app.use(helmet());

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Basic route
app.get('/', (req, res) => {
  res.json({ 
    message: 'Personal Ai API Server is running!', 
    environment: process.env.NODE_ENV || 'development'
  });
});
app.use('/api/v1/users', userRouter);
app.use('/api/v1/fastapi', fastapiRouter);

// app.all('*', (req, res, next) => {
//   next(new AppError(`Can't find ${req.originalUrl} on this server!`, 404));
// });

// 3) Global error handling middleware
app.use(globalErrorHandler);

module.exports = app;