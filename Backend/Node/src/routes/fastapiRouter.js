const router = require('express').Router();
const { protect, restrictTo } = require('../controllers/authController');
const fastapiController = require('../controllers/fastapiController');

router.get('/user-data', protect, restrictTo('user','admin'), fastapiController.getUserData);
router.get('/getUserAuthDetails', protect, restrictTo('user','admin'), fastapiController.getUserAuthDetails);
router.get('/getHistory', protect, restrictTo('user','admin'), fastapiController.getHistory);
router.get('/getemail', protect, restrictTo('user','admin'), fastapiController.getemail);
router.post('/save-chat-history', protect, restrictTo('user','admin'), fastapiController.saveChatHistory);
router.post('/setUserOAuthInfo', protect, restrictTo('user','admin'), fastapiController.setUserOAuthInfo);
module.exports = router;