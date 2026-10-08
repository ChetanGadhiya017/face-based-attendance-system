INSERT INTO division (DIVISION_ID, DIVISION_NAME, PROGRAM_ID, MAX_STUDENTS) VALUES
    ('D1', 'Division 1', 'BTECH_CSE', 70),
    ('D2', 'Division 2', 'BTECH_CSE', 70),
    ('D3', 'Division 3', 'BTECH_CSE', 70),
    ('D4', 'Division 4', 'BTECH_CSE', 70),
    ('D5', 'Division 5', 'BTECH_CSE', 70),
    ('D6', 'Division 6', 'BTECH_CSE', 70),
    ('D7', 'Division 7', 'BTECH_CSE', 70);


-- Insert NEW divisions specifically for the BTECH_ICT program
INSERT INTO DIVISION (DIVISION_ID, DIVISION_NAME, PROGRAM_ID, MAX_STUDENTS) VALUES
('D1_ICT', 'Division 1 - ICT', 'BTECH_ICT', 90), -- Adjust MAX_STUDENTS if needed
('D2_ICT', 'Division 2 - ICT', 'BTECH_ICT', 90),
('D3_ICT', 'Division 3 - ICT', 'BTECH_ICT', 90);
-- Use INSERT IGNORE or check existence if you might run this multiple times


-- Insert the specific division for Civil Engineering students
INSERT IGNORE INTO DIVISION (DIVISION_ID, DIVISION_NAME, PROGRAM_ID, MAX_STUDENTS)
VALUES ('D1_CIV', 'Division 1 - Civil', 'BTECH_CIV', 70); -- Adjust MAX_STUDENTS if needed


-- mech
-- Insert the specific divisions for Mechanical Engineering students
INSERT IGNORE INTO DIVISION (DIVISION_ID, DIVISION_NAME, PROGRAM_ID, MAX_STUDENTS) VALUES
('D1_ME', 'Division 1 - Mechanical', 'BTECH_ME', 70), -- Adjust MAX_STUDENTS if needed
('D2_ME', 'Division 2 - Mechanical', 'BTECH_ME', 70);


-- ece 
-- Insert the specific divisions for Electronics and Communication Engineering students
INSERT IGNORE INTO DIVISION (DIVISION_ID, DIVISION_NAME, PROGRAM_ID, MAX_STUDENTS) VALUES
('D1_ECE', 'Division 1 - EC', 'BTECH_ECE', 70), -- Adjust MAX_STUDENTS if needed
('D2_ECE', 'Division 2 - EC', 'BTECH_ECE', 70),
('D3_ECE', 'Division 3 - EC', 'BTECH_ECE', 70);