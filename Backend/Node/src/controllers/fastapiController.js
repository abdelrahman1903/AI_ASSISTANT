const User = require("../models/userModel");
const AppError = require("../utils/appError");
const catchAsync = require("../utils/catchAsync");


exports.getUserData = async (req, res, next) => {
  const user = await User.findById(req.user.id);
  if (!user) {
    return next(new AppError("No User found", 404));
  }
  res.status(200).json({
    status: "success",
    data: {
      user,
    },
  });
};

exports.saveChatHistory = async (req, res, next) => {
  try {
    console.log("in save history");
    const raw_array = req.body;
    const history_array = raw_array.history;
    if (!Array.isArray(history_array) || history_array.length === 0) {
      return next(new AppError("Invalid chat history data", 400));
    }
    const user = await User.findById(req.user.id);
    if (!user) {
      return next(new AppError("No User found", 404));
    }
    // build plain objects (no _id)
    const newHistory = history_array.map(({ role, content }) => ({
      role,
      content,
    }));

    await User.updateOne(
      { _id: req.user.id },
      { $set: { chatHistory: newHistory } }
    );

    res.status(200).json({
      status: "success",
      data: "Chat history saved successfully",
    });
  } catch (err) {
    console.error(err);
    res.status(400).json({
      status: "error",
      data: {
        err,
      },
    });
  }
};

exports.setUserOAuthInfo = async (req, res, next) => {
  try {
    const {
      access_token,
      refresh_token,
      access_token_expiry,
      is_authenticated,
    } = req.body;

    // Update the user
    const updatedUser = await User.findByIdAndUpdate(
      req.user.id,
      {
        access_token,
        refresh_token,
        access_token_expiry: new Date(access_token_expiry),
        is_authenticated,
      },
      { new: true } // return updated document
    );

    if (!updatedUser) {
      return next(new AppError("No User found", 404));
    }

    res.status(200).json({
      status: "success",
      data: {
        user: updatedUser,
      },
    });
  } catch (err) {
    next(err);
  }
};


exports.getUserAuthDetails = async (req, res, next) => {
  try {
    // Select only the required authentication-related fields
    const user = await User.findById(req.user.id).select(
      "is_authenticated email access_token refresh_token access_token_expiry"
    );

    if (!user) {
      return next(new AppError("No User found", 404));
    }

    res.status(200).json({
      status: "success",
      data: {
        is_authenticated: user.is_authenticated,
        email: user.email,
        access_token: user.access_token,
        refresh_token: user.refresh_token,
        access_token_expiry: user.access_token_expiry,
      },
    });
  } catch (err) {
    next(err);
  }
};

exports.getHistory = async (req, res, next) => {
  try {
    const user = await User.findById(req.user.id).select("chatHistory"); // only select this field

    if (!user) {
      return next(new AppError("No User found", 404));
    }

    res.status(200).json({
      status: "success",
      data: {
        chatHistory: user.chatHistory,
      },
    });
  } catch (err) {
    next(err);
  }
};

exports.getemail = async (req, res, next) => {
  try {
    const user = await User.findById(req.user.id).select("email"); // only select this field

    if (!user) {
      return next(new AppError("No User found", 404));
    }

    res.status(200).json({
      status: "success",
      data: {
        email: user.email,
      },
    });
  } catch (err) {
    next(err);
  }
};