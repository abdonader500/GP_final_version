// controllers/auth.controller.js
const User = require('../models/user.model');
const jwt = require('jsonwebtoken');

// Create JWT token
const generateToken = (user) => {
  return jwt.sign(
    { id: user._id, username: user.username, role: user.role },
    process.env.JWT_SECRET || 'your_jwt_secret',
    { expiresIn: '24h' }
  );
};

// Register a new user
exports.register = async (req, res) => {
  try {
    const { username, password, role, email, name } = req.body;

    // Check if username already exists
    const existingUser = await User.findOne({ username });
    if (existingUser) {
      return res.status(400).json({ 
        success: false, 
        message: 'اسم المستخدم مسجل بالفعل' 
      });
    }

    // Validate role
    if (role && !['user', 'admin'].includes(role)) {
      return res.status(400).json({ 
        success: false, 
        message: 'دور المستخدم غير صالح' 
      });
    }

    // Create new user
    const user = new User({
      username,
      password,
      role: role || 'user',
      email,
      name
    });

    await user.save();

    // Generate token
    const token = generateToken(user);

    res.status(201).json({
      success: true,
      message: 'تم إنشاء المستخدم بنجاح',
      user,
      token
    });
  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({
      success: false,
      message: 'خطأ في إنشاء المستخدم',
      error: error.message
    });
  }
};

// Login
exports.login = async (req, res) => {
  try {
    const { username, password, role } = req.body;

    // Find user
    const user = await User.findOne({ username });
    
    // Check if user exists
    if (!user) {
      return res.status(401).json({
        success: false,
        message: 'اسم المستخدم أو كلمة المرور غير صحيحة'
      });
    }

    // Verify role if provided
    if (role && user.role !== role) {
      return res.status(403).json({
        success: false,
        message: 'ليس لديك صلاحية للوصول كـ ' + role
      });
    }

    // Check if account is active
    if (!user.active) {
      return res.status(403).json({
        success: false,
        message: 'الحساب معطل. يرجى التواصل مع المسؤول'
      });
    }

    // Check password
    const isMatch = await user.comparePassword(password);
    if (!isMatch) {
      return res.status(401).json({
        success: false,
        message: 'اسم المستخدم أو كلمة المرور غير صحيحة'
      });
    }

    // Update last login time
    user.lastLogin = Date.now();
    await user.save();

    // Generate token
    const token = generateToken(user);

    res.status(200).json({
      success: true,
      message: 'تم تسجيل الدخول بنجاح',
      user,
      token
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({
      success: false,
      message: 'خطأ في تسجيل الدخول',
      error: error.message
    });
  }
};

// Get current user profile
exports.getProfile = async (req, res) => {
  try {
    const user = await User.findById(req.user.id);
    
    if (!user) {
      return res.status(404).json({
        success: false,
        message: 'المستخدم غير موجود'
      });
    }
    
    res.status(200).json({
      success: true,
      user
    });
  } catch (error) {
    console.error('Get profile error:', error);
    res.status(500).json({
      success: false,
      message: 'خطأ في استرجاع بيانات المستخدم',
      error: error.message
    });
  }
};