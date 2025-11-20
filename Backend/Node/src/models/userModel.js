const mongoose = require("mongoose");
const validator = require("validator");
const bcrypt = require("bcryptjs");
const crypto = require("crypto");

const { Schema } = mongoose;

const userSchema = new Schema(
  {
    name: {
      type: String,
      required: [true, "A user must have a name"],
      trim: true,
      maxlength: [40, "A user name must have less or equal than 40 characters"],
      minlength: [3, "A user name must have more or equal than 3 characters"],
    },
    email: {
      type: String,
      required: [true, "A user must have an email"],
      unique: true,
      lowercase: true,
      validate: [validator.isEmail, "Please provide a valid email"],
    },
    photo: {
      type: String,
      default: "default.jpg",
    },
    password: {
      type: String,
      required: [true, "A user must have a password"],
      minlength: [8, "A password must have more or equal than 8 characters"],
      select: false, // Do not return password in queries
    },
    passwordConfirm: {
      type: String,
      required: [true, "Please confirm your password"],
      validate: {
        // This only works on CREATE and SAVE
        validator: function (el) {
          return el === this.password; // 'this' points to the current document
        },
        message: "Passwords are not the same!",
      },
      select: false, // Do not return passwordConfirm in queries
    },
    // status: {
    //   type: String,
    //   enum: ["active", "inactive", "suspended"],
    //   default: "active",
    //   required: true,
    // },
    role: {
      type: String,
      enum: ["user", "admin"],
      default: "user",
      required: true,
    },

    // Patient-specific fields
    age: { type: Number },
    gender: { type: String, enum: ["male", "female"] },
    chatHistory: [
      {
        // _id: false,
        role: { type: String, enum: ["user", "model"], required: true },
        content: { type: String, required: true },
      },
    ],
    // Admin-specific fields
    permissions: [{ type: String }],
    passwordChangedAt: {
      type: Date,
    },
    passwordResetToken: String,
    passwordResetExpires: Date,
    active: {
      type: Boolean,
      default: true,
      select: false, // Do not return active in queries
    },
    access_token: {
      type: String,
      default: null, // no token initially
    },
    refresh_token: {
      type: String,
      default: null, // no token initially
    },
    access_token_expiry: {
      type: Date,
      default: null, // will store expiry datetime
    },
    is_authenticated: {
      type: Boolean,
      default: false, // user not authenticated by default
    },
    // email_provider  : { // optional ("gmail") — in case you add Outlook later
    //   type: String,
    //   default: null, // no token initially
    // },
  },
  { timestamps: true }
);

userSchema.pre("save", async function (next) {
  // Only run this function if password was modified
  if (!this.isModified("password")) return next();

  // Hash the password with cost of 12
  this.password = await bcrypt.hash(this.password, 12);

  // Delete passwordConfirm field
  this.passwordConfirm = undefined;
  next();
});

userSchema.pre("save", function (next) {
  // If password is not modified, skip this step
  if (!this.isModified("password") || this.isNew) return next();
  // Set passwordChangedAt to current time
  this.passwordChangedAt = Date.now() - 1000; // Subtract 1
  next();
});

userSchema.methods.correctPassword = async function (
  candidatePassword,
  userPassword
) {
  // Compare candidate password with the stored hashed password
  return await bcrypt.compare(candidatePassword, userPassword);
};
userSchema.pre(/^find/, function (next) {
  // This middleware will run before every find query
  this.find({ active: { $ne: false } }); // Exclude inactive users
  next();
});

userSchema.methods.changedPasswordAfter = function (JWTTimestamp) {
  // Check if the password was changed after the JWT was issued
  if (this.passwordChangedAt) {
    const changedTimestamp = parseInt(
      this.passwordChangedAt.getTime() / 1000,
      10
    ); // Convert to seconds
    return JWTTimestamp < changedTimestamp; // If JWT timestamp is less than the changed timestamp, password was changed
  }
  // If passwordChangedAt is not set, return false
  return false;
};

userSchema.methods.createPasswordResetToken = function () {
  // Create a reset token and set it to expire in 10 minutes
  const resetToken = crypto.randomBytes(32).toString("hex");
  this.passwordResetToken = crypto
    .createHash("sha256")
    .update(resetToken)
    .digest("hex");
  this.passwordResetExpires = Date.now() + 10 * 60 * 1000; // 10 minutes
  console.log("Hashed Reset Token:", this.passwordResetToken); // Log the hashed token
  return resetToken; // Return the plain text token
};

const User = mongoose.model("User", userSchema);
module.exports = User;
