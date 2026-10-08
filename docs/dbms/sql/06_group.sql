INSERT INTO STUDENT_GROUP (GROUP_ID, GROUP_NAME, DIVISION_ID) VALUES 
('G1', 'Group 1', 'D1'),
('G2', 'Group 2', 'D1'),
('G3', 'Group 3', 'D2'),
('G4', 'Group 4', 'D2'),
('G5', 'Group 5', 'D3'),
('G6', 'Group 6', 'D3'),
('G7', 'Group 7', 'D4'),
('G8', 'Group 8', 'D4'),
('G9', 'Group 9', 'D5'),
('G10', 'Group 10', 'D5'),
('G11', 'Group 11', 'D6'),
('G12', 'Group 12', 'D6'),
('G13', 'Group 13', 'D7'),
('G14', 'Group 14', 'D7');

-- adding new groups

-- Ensure groups H1-H6 are linked to the NEW ICT Division IDs
-- Check existing links first: SELECT * FROM STUDENT_GROUP WHERE GROUP_ID IN ('H1', 'H2', 'H3', 'H4', 'H5', 'H6');

-- If they exist but are linked incorrectly (e.g., to D1, D2, D3), UPDATE them:
-- UPDATE STUDENT_GROUP SET DIVISION_ID = 'D1_ICT' WHERE GROUP_ID IN ('H1', 'H2');
-- UPDATE STUDENT_GROUP SET DIVISION_ID = 'D2_ICT' WHERE GROUP_ID IN ('H3', 'H4');
-- UPDATE STUDENT_GROUP SET DIVISION_ID = 'D3_ICT' WHERE GROUP_ID IN ('H5', 'H6');

-- If they don't exist, INSERT them linked correctly:
INSERT IGNORE INTO STUDENT_GROUP (GROUP_ID, GROUP_NAME, DIVISION_ID) VALUES
('H1', 'Group H1', 'D1_ICT'),
('H2', 'Group H2', 'D1_ICT'),
('H3', 'Group H3', 'D2_ICT'),
('H4', 'Group H4', 'D2_ICT'),
('H5', 'Group H5', 'D3_ICT'),
('H6', 'Group H6', 'D3_ICT');


-- civil 
-- Insert the specific groups for the Civil division
INSERT IGNORE INTO STUDENT_GROUP (GROUP_ID, GROUP_NAME, DIVISION_ID) VALUES
('D1', 'Group D1', 'D1_CIV'),
('D2', 'Group D2', 'D1_CIV');


-- mech 
-- Insert the specific groups for the Mechanical divisions
INSERT IGNORE INTO STUDENT_GROUP (GROUP_ID, GROUP_NAME, DIVISION_ID) VALUES
('A1', 'Group A1', 'D1_ME'),
('A2', 'Group A2', 'D1_ME'),
('A3', 'Group A3', 'D2_ME'),
('A4', 'Group A4', 'D2_ME');


-- ece 
-- Insert the specific groups for the EC divisions
INSERT IGNORE INTO STUDENT_GROUP (GROUP_ID, GROUP_NAME, DIVISION_ID) VALUES
('F1', 'Group F1', 'D1_ECE'),
('F2', 'Group F2', 'D1_ECE'),
('F3', 'Group F3', 'D2_ECE'),
('F4', 'Group F4', 'D2_ECE'),
('F5', 'Group F5', 'D3_ECE'),
('F6', 'Group F6', 'D3_ECE');