-- =============================================
-- SmartAlloc Database Setup
-- Run this in phpMyAdmin
-- =============================================

CREATE DATABASE IF NOT EXISTS smartalloc;
USE smartalloc;

-- Users table (Admin, Volunteer, NGO)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin','volunteer','ngo') NOT NULL,
    volunteer_id VARCHAR(20) NULL,
    phone VARCHAR(20),
    location VARCHAR(200),
    skills TEXT,
    profile_pic VARCHAR(255) DEFAULT 'default.png',
    status ENUM('active','inactive','pending') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NGO Organizations table
CREATE TABLE IF NOT EXISTS ngos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    org_name VARCHAR(150) NOT NULL,
    org_type VARCHAR(100),
    registration_no VARCHAR(100),
    address TEXT,
    logo VARCHAR(255) DEFAULT 'ngo_default.png',
    verified TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tasks / Needs table
CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    location VARCHAR(200),
    latitude DECIMAL(10,8) DEFAULT 11.0168,
    longitude DECIMAL(11,8) DEFAULT 76.9558,
    problem_type ENUM('food','medical','shelter','water','education','other') DEFAULT 'other',
    urgency INT DEFAULT 3 CHECK (urgency BETWEEN 1 AND 5),
    status ENUM('open','in-progress','completed') DEFAULT 'open',
    volunteers_needed INT DEFAULT 1,
    created_by INT,
    ngo_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (ngo_id) REFERENCES ngos(id)
);

-- Volunteer Assignments
CREATE TABLE IF NOT EXISTS assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT,
    volunteer_id INT,
    status ENUM('pending','accepted','in-progress','completed','declined') DEFAULT 'pending',
    progress INT DEFAULT 0,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (volunteer_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    message TEXT,
    is_read TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Chat messages
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT,
    receiver_id INT,
    task_id INT NULL,
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id),
    FOREIGN KEY (receiver_id) REFERENCES users(id)
);

-- =============================================
-- SEED DATA - Default Users
-- Password for all: admin123 (hashed)
-- =============================================

INSERT INTO users (name, email, password, role, volunteer_id, phone, location, skills) VALUES
('Admin User', 'admin@smartalloc.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin', NULL, '9999999999', 'Chennai', 'management'),
('John Smith', 'john@example.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'volunteer', 'VOL001', '9876543210', 'Chennai Downtown', 'medical,driving,teaching'),
('Sarah Johnson', 'sarah@example.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'volunteer', 'VOL002', '9876543211', 'Chennai Northside', 'teaching,food,shelter'),
('Red Cross', 'redcross@example.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'ngo', NULL, '9876543212', 'Chennai', 'medical,food');

INSERT INTO ngos (user_id, org_name, org_type, registration_no, address, verified) VALUES
(4, 'Red Cross Society', 'Humanitarian', 'NGO2024001', 'Anna Salai, Chennai', 1);

INSERT INTO tasks (title, description, location, problem_type, urgency, status, volunteers_needed, created_by, ngo_id, latitude, longitude) VALUES
('Food Distribution Drive', 'Distribute food packets to 500 families in flood-affected area', 'Downtown Chennai', 'food', 5, 'open', 10, 1, 1, 13.0827, 80.2707),
('Medical Camp Setup', 'Setup and run a free medical camp for 200 patients', 'Northside Chennai', 'medical', 4, 'open', 5, 1, 1, 13.1067, 80.2206),
('School Supplies Distribution', 'Distribute notebooks and stationery to 300 children', 'Eastside Chennai', 'education', 2, 'in-progress', 3, 1, 1, 13.0569, 80.2425),
('Shelter Support', 'Help set up temporary shelters for displaced families', 'Southside Chennai', 'shelter', 4, 'open', 8, 1, 1, 12.9716, 80.2200),
('Clean Water Distribution', 'Distribute 500L water cans to affected areas', 'West Chennai', 'water', 5, 'open', 6, 1, 1, 13.0500, 80.1800);

INSERT INTO assignments (task_id, volunteer_id, status, progress) VALUES
(1, 2, 'in-progress', 40),
(2, 2, 'accepted', 0),
(3, 3, 'in-progress', 70);

INSERT INTO notifications (user_id, message) VALUES
(2, 'You have been assigned to Food Distribution Drive'),
(2, 'Medical Camp needs 2 more nurses urgently'),
(3, 'Your progress on School Supplies task has been noted'),
(4, 'New volunteer John Smith accepted your task');

SELECT 'Database setup complete! You can now login.' AS message;
