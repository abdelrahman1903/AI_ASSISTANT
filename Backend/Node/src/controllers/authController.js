const User = require('../models/userModel');
const catchAsync = require('../utils/catchAsync');
const AppError = require('../utils/appError');
const jwt = require('jsonwebtoken');
const { promisify } = require('util');
const { sendEmail } = require('../utils/email');
const crypto = require('crypto');




const signToken = (id) => {
    return jwt.sign({ id }, process.env.JWT_SECRET, {
        expiresIn: process.env.JWT_EXPIRES_IN
    });
};

// Function to create and send a JWT token in the response
const createSendToken = (user, statusCode, res) => {
    const token = signToken(user._id);
    res.cookie('jwt', token, {
        expires: new Date(Date.now() + process.env.JWT_COOKIE_EXPIRES * 24 * 60 * 60 * 1000), // Convert days to milliseconds
        httpOnly: true, // Prevents client-side JavaScript from accessing the cookie
        secure: process.env.NODE_ENV === 'production', // Set to true in production to use HTTPS
        sameSite: 'Strict' // Prevents CSRF attacks by ensuring the cookie is sent only for same-site requests
    });

    user.password = undefined; // Remove password from response
    
    res.status(statusCode).json({
        status: 'success',
        token: token,
        message: 'User created successfully',
        data: {
            user: user
        }
    });
};

// Register a new user
exports.signup = catchAsync(async (req, res, next) => {
    const {name, email, password, passwordConfirm, photo, role} = req.body;
    const newUser = await User.create({
        name,
        email,
        password,
        passwordConfirm,
        photo, // Optional, can be set to a default value in the model,
        role // Optional, can be set to a default value in the model
    });

    createSendToken(newUser, 201, res);
    
});

exports.login = catchAsync(async (req, res, next) => {
    const {email, password} = req.body;

    //1) check if email and password exist
    if(!email || !password){
        return next(new AppError('Please provide email and password!!',400));
    }

    //2) get the user by email
    const user = await User.findOne({email}).select('+password');
    
    if(!user || !(await user.correctPassword(password, user.password))){
        return next(new AppError('Incorrect email or password!!', 401));
    }

    //3) if everything is ok, send token
    createSendToken(user, 200, res);
});

exports.protect = catchAsync(async (req, res, next) => {
    //1) Get token from header
    let token;
    if(req.headers.authorization && req.headers.authorization.startsWith('Bearer')){
        token = req.headers.authorization.split(' ')[1];
    }

    if(!token){
        return next(new AppError('You are not logged in! Please log in to get access.', 401));
    }

    //2) Verify token
    const decoded = await promisify(jwt.verify)(token, process.env.JWT_SECRET);
    const currentUser = await User.findById(decoded.id);
    // console.log(currentUser);

    //3) Check if user still exists
    if(!currentUser){
        return next(new AppError('The user belonging to this token does no longer exist.', 401));
    }

    //4) Check if user changed password after the token was issued
    if(currentUser.changedPasswordAfter(decoded.iat)){
        return next(new AppError('User recently changed password! Please log in again.', 401));
    }

    // Grant access to protected route
    req.user = currentUser; // Attach user to request object
    next();
});

exports.restrictTo = (...roles) => {
    return (req, res, next) => {
        // roles is an array e.g. ['admin', 'lead-guide']
        if(!roles.includes(req.user.role)){
            return next(new AppError('You do not have permission to perform this action', 403));
        }
        next();
    };
};

exports.forgotPassword = catchAsync(async (req, res, next) => {
    const {email} = req.body;

    //1) Get user based on posted email
    const user = await User.findOne({email});
    console.log('User found:', user); // Log the user object
    if(!user){
        return next(new AppError('There is no user with this email address.', 404));
    }
    //2) Generate random reset token
    const resetToken = user.createPasswordResetToken();
    await user.save({ validateBeforeSave: false }); // Skip validation when saving
    
    //3) Send it to user's email
    const resetURL = `${req.protocol}://${req.get('host')}/api/v1/users/resetPassword/${resetToken}`;
    const message = `Forgot your password? Submit a PATCH request with your new password and passwordConfirm to: ${resetURL}.\nIf you didn't forget your password, please ignore this email.`;

    const options = {
        email: user.email,
        subject: 'Your password reset token (valid for 10 minutes)',
        message: message
    };

    try {
        console.log('Sending email to:', options.email);
        await sendEmail(options);
        console.log('Email sent');
        res.status(200).json({
            status: 'success',
            message: 'Token sent to email!'
        });
    } catch (err) {
        console.error('❌ Email sending error:', err); // 👈 Log the actual Nodemailer error

        user.passwordResetToken = undefined;
        user.passwordResetExpires = undefined;
        await user.save({ validateBeforeSave: false });

        return next(new AppError('There was an error sending the email. Try again later!', 500));
    }

});

exports.resetPassword = catchAsync(async (req, res, next) => {
    // 1) Get user based on the token
    const hashedToken = crypto
        .createHash('sha256')
        .update(req.params.token)
        .digest('hex');

    const user = await User.findOne({
        passwordResetToken: hashedToken,
        passwordResetExpires: { $gt: Date.now() }
    });

    // 2) If token has not expired, and there is user, set the new password
    if (!user) {
        return next(new AppError('Token is invalid or has expired', 400));
    }
    
    user.password = req.body.password;
    user.passwordConfirm = req.body.passwordConfirm;
    user.passwordResetToken = undefined;
    user.passwordResetExpires = undefined;
    
    await user.save(); // Run validators to ensure password and passwordConfirm match

    // 3) Log the user in, send JWT
    createSendToken(user, 200, res);
});

exports.updatePassword = catchAsync(async (req, res, next) => {
    // 1) Get user from collection
    const user = await User.findById(req.user.id).select('+password');
    
    // 2) Check if POSTed current password is correct
    if(!await user.correctPassword(req.body.currentPassword, user.password)){
        return next(new AppError('Your current password is wrong.', 401));
    }

    // 3) If so, update password
    user.password = req.body.password;
    user.passwordConfirm = req.body.passwordConfirm;
    await user.save(); // Run validators to ensure password and passwordConfirm match

    // 4) Log user in, send JWT
    createSendToken(user, 200, res);
});