const express = require('express');
const authController = require('../controllers/authController');

const router = express.Router();

router.post('/signup', authController.signup); // Route for user signup
router.post('/login', authController.login); // Route for user login
router.post('/forgotPassword', authController.forgotPassword); // Route for forgot password
router.patch('/resetPassword/:token', authController.resetPassword); // Route for resetting password

router.use(authController.protect); // Protect all routes after this middleware
router.patch('/updatePassword', authController.updatePassword); // Route for updating password

module.exports = router;