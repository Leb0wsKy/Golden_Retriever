/**
 * Authentication Service
 * Handles user registration, login, and JWT token management
 * Users are stored in Qdrant vector database in 'users' collection
 */

const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { QdrantClient } = require('@qdrant/js-client-rest');
const { randomUUID } = require('crypto');
require('dotenv').config();

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';
const JWT_EXPIRES_IN = '7d'; // Token valid for 7 days

// Initialize Qdrant client
const qdrantClient = new QdrantClient({
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
  timeout: 30000, // 30 second timeout
  checkCompatibility: false, // Skip version check
});

console.log('Auth Service - Qdrant URL:', process.env.QDRANT_URL?.substring(0, 50) + '...');

const USERS_COLLECTION = 'users';

/**
 * Initialize users collection in Qdrant
 */
async function initializeUsersCollection() {
  try {
    const collections = await qdrantClient.getCollections();
    const exists = collections.collections.some(c => c.name === USERS_COLLECTION);
    
    if (!exists) {
      await qdrantClient.createCollection(USERS_COLLECTION, {
        vectors: {
          size: 384, // Embedding size (can use email hash as vector)
          distance: 'Cosine',
        },
      });
      console.log('✅ Users collection created');
    } else {
      console.log('✅ Users collection already exists');
    }
    
    // Create email index (runs whether collection is new or existing)
    try {
      await qdrantClient.createPayloadIndex(USERS_COLLECTION, {
        field_name: 'email',
        field_schema: 'keyword',
      });
      console.log('✅ Email index created/verified');
    } catch (indexError) {
      // Index might already exist, that's okay
      if (!indexError.message?.includes('already exists')) {
        console.warn('⚠️ Email index warning:', indexError.message);
      }
    }
  } catch (error) {
    console.warn('⚠️ Users collection initialization delayed:', error.message);
    console.warn('   Collection will be created on first signup attempt');
    // Don't throw - allow server to start and retry on signup
  }
}

/**
 * Validate password requirements
 * - Minimum 8 characters
 * - At least one number
 * - At least one special character
 */
function validatePassword(password) {
  if (password.length < 8) {
    return { valid: false, message: 'Password must be at least 8 characters long' };
  }
  
  if (!/\d/.test(password)) {
    return { valid: false, message: 'Password must contain at least one number' };
  }
  
  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
    return { valid: false, message: 'Password must contain at least one special character' };
  }
  
  return { valid: true };
}

/**
 * Validate email format
 */
function validateEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Generate a simple vector from email (for Qdrant storage)
 */
function emailToVector(email) {
  const hash = email.split('').reduce((acc, char) => {
    return acc + char.charCodeAt(0);
  }, 0);
  
  // Generate a 384-dimensional vector based on email
  const vector = new Array(384).fill(0).map((_, i) => {
    return Math.sin((hash + i) / 100);
  });
  
  return vector;
}

/**
 * Ensure users collection exists (create if needed)
 */
async function ensureUsersCollection() {
  try {
    const collections = await qdrantClient.getCollections();
    const exists = collections.collections.some(c => c.name === USERS_COLLECTION);
    
    if (!exists) {
      await qdrantClient.createCollection(USERS_COLLECTION, {
        vectors: {
          size: 384,
          distance: 'Cosine',
        },
      });
      
      // Create index on email field for filtering
      await qdrantClient.createPayloadIndex(USERS_COLLECTION, {
        field_name: 'email',
        field_schema: 'keyword',
      });
      
      console.log('✅ Created users collection with email index');
    }
  } catch (error) {
    console.error('Failed to ensure users collection:', error.message);
    throw new Error('Database connection failed');
  }
}

/**
 * Register a new user
 */
async function signup(email, password, name) {
  try {
    // Ensure collection exists before proceeding
    await ensureUsersCollection();
    
    // Validate email
    if (!validateEmail(email)) {
      return { success: false, message: 'Invalid email format' };
    }
    
    // Validate password
    const passwordValidation = validatePassword(password);
    if (!passwordValidation.valid) {
      return { success: false, message: passwordValidation.message };
    }
    
    // Check if user already exists
    const existing = await getUserByEmail(email);
    if (existing) {
      return { success: false, message: 'Email already registered' };
    }
    
    // Hash password
    const hashedPassword = await bcrypt.hash(password, 10);
    
    // Create user ID (UUID format required by Qdrant)
    const userId = randomUUID();
    
    // Store user in Qdrant
    await qdrantClient.upsert(USERS_COLLECTION, {
      wait: true,
      points: [
        {
          id: userId,
          vector: emailToVector(email),
          payload: {
            email: email.toLowerCase(),
            password: hashedPassword,
            name: name || email.split('@')[0],
            createdAt: new Date().toISOString(),
            lastLogin: null,
          },
        },
      ],
    });
    
    // Generate JWT token
    const token = jwt.sign({ userId, email }, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
    
    return {
      success: true,
      message: 'User created successfully',
      token,
      user: {
        id: userId,
        email: email.toLowerCase(),
        name: name || email.split('@')[0],
      },
    };
  } catch (error) {
    console.error('Signup error:', error);
    return { success: false, message: 'Failed to create user' };
  }
}

/**
 * Login user
 */
async function login(email, password) {
  try {
    // Get user by email
    const user = await getUserByEmail(email);
    
    if (!user) {
      return { success: false, message: 'Invalid email or password' };
    }
    
    // Verify password
    const validPassword = await bcrypt.compare(password, user.password);
    
    if (!validPassword) {
      return { success: false, message: 'Invalid email or password' };
    }
    
    // Update last login
    await qdrantClient.setPayload(USERS_COLLECTION, {
      wait: true,
      points: [user.id],
      payload: {
        lastLogin: new Date().toISOString(),
      },
    });
    
    // Generate JWT token
    const token = jwt.sign({ userId: user.id, email: user.email }, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
    
    return {
      success: true,
      message: 'Login successful',
      token,
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
      },
    };
  } catch (error) {
    console.error('Login error:', error);
    return { success: false, message: 'Login failed' };
  }
}

/**
 * Get user by email
 */
async function getUserByEmail(email) {
  try {
    const result = await qdrantClient.scroll(USERS_COLLECTION, {
      filter: {
        must: [
          {
            key: 'email',
            match: { value: email.toLowerCase() },
          },
        ],
      },
      limit: 1,
    });
    
    if (result.points.length > 0) {
      const point = result.points[0];
      return {
        id: point.id,
        ...point.payload,
      };
    }
    
    return null;
  } catch (error) {
    console.error('Error getting user:', error);
    return null;
  }
}

/**
 * Verify JWT token
 */
function verifyToken(token) {
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    return { valid: true, data: decoded };
  } catch (error) {
    return { valid: false, message: 'Invalid token' };
  }
}

/**
 * Middleware to protect routes
 */
function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN
  
  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }
  
  const verification = verifyToken(token);
  
  if (!verification.valid) {
    return res.status(403).json({ error: 'Invalid or expired token' });
  }
  
  req.user = verification.data;
  next();
}

module.exports = {
  initializeUsersCollection,
  signup,
  login,
  verifyToken,
  authenticateToken,
};
