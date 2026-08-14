CREATE DATABASE IF NOT EXISTS rbac_db;
USE rbac_db;

-- Users Table
CREATE TABLE IF NOT EXISTS users_1 (
    user_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE NOT NULL
);

-- Resources Table
CREATE TABLE IF NOT EXISTS resources_1 (
    r_id VARCHAR(50) PRIMARY KEY,
    resource_name VARCHAR(100),
    resource_type ENUM(
        'REST_API',
        'DATABASE_TABLE',
        'FILE_DOCUMENT',
        'MODEL_ENDPOINT'
    ) DEFAULT 'REST_API',
    api_endpoint VARCHAR(255),
    http_method ENUM('GET', 'POST', 'PUT', 'DELETE') DEFAULT 'GET',
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Groups Table
CREATE TABLE IF NOT EXISTS groups_1 (
    group_id INT PRIMARY KEY,
    group_name VARCHAR(100),
    team_lead_id VARCHAR(50),
    FOREIGN KEY (team_lead_id)
        REFERENCES users_1(user_id)
);

-- Access Requests Table
CREATE TABLE IF NOT EXISTS access_requests_1 (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50),
    resource_id VARCHAR(50),
    approval_token VARCHAR(255) UNIQUE,
    status ENUM('PENDING', 'APPROVED', 'REJECTED') DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users_1(user_id),

    FOREIGN KEY (resource_id)
        REFERENCES resources_1(r_id)
);

-- User-Group Junction Table
CREATE TABLE IF NOT EXISTS user_groups_1 (
    user_id VARCHAR(50),
    group_id INT,

    PRIMARY KEY (user_id, group_id),

    FOREIGN KEY (user_id)
        REFERENCES users_1(user_id),

    FOREIGN KEY (group_id)
        REFERENCES groups_1(group_id)
);

-- Group-Resource Junction Table
CREATE TABLE IF NOT EXISTS group_resources_1 (
    group_id INT,
    resource_id VARCHAR(50),

    PRIMARY KEY (group_id, resource_id),

    FOREIGN KEY (group_id)
        REFERENCES groups_1(group_id),

    FOREIGN KEY (resource_id)
        REFERENCES resources_1(r_id)
);

INSERT INTO users_1 (user_id, name, email) VALUES
('U001', 'John Admin', 'john.admin@company.com'),
('U002', 'Sarah TeamLead', 'sarah.lead@company.com'),
('U003', 'David Developer', 'david.dev@company.com'),
('U004', 'Priya Analyst', 'priya.analyst@company.com'),
('U005', 'Michael Engineer', 'michael.eng@company.com'),
('U006', 'Emma Scientist', 'emma.ds@company.com'),
('U007', 'Raj Tester', 'raj.tester@company.com'),
('U008', 'Lisa Manager', 'lisa.manager@company.com');

INSERT INTO resources_1
(r_id, resource_name, resource_type, api_endpoint, http_method, description)
VALUES

('R001', 'Employee API', 'REST_API',
 '/api/employees', 'GET',
 'Fetch employee information'),

('R002', 'Payroll API', 'REST_API',
 '/api/payroll', 'POST',
 'Manage payroll data'),

('R003', 'Customer Table', 'DATABASE_TABLE',
 NULL, 'GET',
 'Customer database table'),

('R004', 'Sales Table', 'DATABASE_TABLE',
 NULL, 'GET',
 'Sales records'),

('R005', 'HR Policy Document', 'FILE_DOCUMENT',
 NULL, 'GET',
 'Company HR policies'),

('R006', 'Financial Report', 'FILE_DOCUMENT',
 NULL, 'GET',
 'Quarterly financial reports'),

('R007', 'Recommendation Model', 'MODEL_ENDPOINT',
 '/model/recommendation', 'POST',
 'ML recommendation model'),

('R008', 'Fraud Detection Model', 'MODEL_ENDPOINT',
 '/model/fraud-detection', 'POST',
 'AI model for fraud analytics');
 
 INSERT INTO groups_1
(group_id, group_name, team_lead_id)
VALUES

(101, 'Administrators', 'U001'),
(102, 'Developers', 'U002'),
(103, 'Data Analysts', 'U004'),
(104, 'AI Engineers', 'U005'),
(105, 'QA Team', 'U007');

INSERT INTO user_groups_1
(user_id, group_id)
VALUES

('U001', 101),
('U002', 102),
('U003', 102),
('U004', 103),
('U005', 104),
('U006', 104),
('U007', 105);

INSERT INTO group_resources_1
(group_id, resource_id)
VALUES

(101,'R001'),
(101,'R002'),
(101,'R003'),
(101,'R004'),
(101,'R005'),
(101,'R006'),
(101,'R007'),
(101,'R008');

INSERT INTO group_resources_1
(group_id, resource_id)
VALUES

(102,'R001'),
(102,'R003'),
(102,'R004');

INSERT INTO group_resources_1
(group_id, resource_id)
VALUES

(103,'R003'),
(103,'R004'),
(103,'R006');

INSERT INTO group_resources_1
(group_id, resource_id)
VALUES

(104,'R007'),
(104,'R008'),
(104,'R003');

INSERT INTO group_resources_1
(group_id, resource_id)
VALUES

(105,'R001'),
(105,'R005');


INSERT INTO access_requests_1
(user_id, resource_id, approval_token, status)
VALUES
('U003', 'R007', 'TOKEN_DEV_AI_001', 'PENDING');


INSERT INTO access_requests_1
(user_id, resource_id, approval_token, status)
VALUES

('U006', 'R006', 'TOKEN_DS_FIN_001', 'APPROVED'),

('U005', 'R002', 'TOKEN_AI_PAYROLL_001', 'PENDING'),

('U002', 'R008', 'TOKEN_LEAD_AI_001', 'APPROVED');
