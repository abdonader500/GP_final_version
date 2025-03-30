// backend/middleware/auth.js
const jwt = require('jsonwebtoken');
const User = require('../models/user.model');

// Middleware to authenticate token
exports.authenticateToken = async (req, res, next) => {
  try {
    // Get token from header
    const authHeader = req.headers.authorization;
    const token = authHeader && authHeader.split(' ')[1];
    
    if (!token) {
      return res.status(401).json({ 
        success: false, 
        message: 'الوصول مرفوض. يرجى تسجيل الدخول' 
      });
    }

    // Verify token
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'your_jwt_secret');
    
    // Check if user exists
    const user = await User.findById(decoded.id);
    if (!user) {
      return res.status(404).json({ 
        success: false, 
        message: 'المستخدم غير موجود' 
      });
    }
    
    // Check if user is active
    if (!user.active) {
      return res.status(403).json({ 
        success: false, 
        message: 'الحساب معطل. يرجى التواصل مع المسؤول' 
      });
    }
    
    // Add user info to request
    req.user = decoded;
    next();
  } catch (error) {
    console.error('Authentication error:', error);
    return res.status(403).json({ 
      success: false, 
      message: 'جلسة العمل منتهية. يرجى تسجيل الدخول مرة أخرى',
      error: error.message
    });
  }
};

// Middleware to authorize admin
exports.authorizeAdmin = (req, res, next) => {
  if (req.user && req.user.role === 'admin') {
    next();
  } else {
    return res.status(403).json({ 
      success: false, 
      message: 'غير مصرح. يتطلب صلاحيات المسؤول' 
    });
  }
};