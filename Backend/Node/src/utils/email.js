const nodemailer = require('nodemailer');

exports.sendEmail = async (options) => {
  // ✅ Create the transporter inside the function
  const transporter = nodemailer.createTransport({
    host: process.env.EMAIL_HOST,
    port: process.env.EMAIL_PORT,
    secure: false, // For Mailtrap use false (Port 587)
    auth: {
      user: process.env.EMAIL_USERNAME,
      pass: process.env.EMAIL_PASSWORD,
    },
  });

  // ✅ Optional: verify connection config
  transporter.verify((error, success) => {
    if (error) {
      console.error('❌ SMTP Connection Failed:', error);
    } else {
      console.log('✅ SMTP Server is ready to send emails');
    }
  });

  // ✅ Define email options
  const mailOptions = {
    from: 'Natours <natours@example.com>',
    to: options.email,
    subject: options.subject,
    text: options.message,
    // html: options.html // Optional
  };

  // ✅ Send the email
  await transporter.sendMail(mailOptions);
};

exports.sendWelcomeEmail = async (user) => {
  const options = {
    email: user.email,
    subject: 'Welcome to Natours!',
    message: `Hello ${user.name},\n\nThank you for joining Natours! We're excited to have you on board.\n\nBest regards,\nThe Natours Team`,
  };

  await this.sendEmail(options);
};