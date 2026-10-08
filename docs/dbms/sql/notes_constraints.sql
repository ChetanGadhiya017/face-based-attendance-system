SELECT CONSTRAINT_NAME 
FROM information_schema.TABLE_CONSTRAINTS 
WHERE TABLE_NAME = 'STUDENT' 
AND CONSTRAINT_TYPE = 'CHECK';
-- the above is for getting the constraint name 

-- example for dropping constraint
ALTER TABLE STUDENT DROP CHECK student_chk_1;

-- adding new constraint to a field
ALTER TABLE STUDENT ADD CONSTRAINT student_chk_1 CHECK (ID REGEXP '^[0-9]{2}[A-Z]{3}[0-9]{3}D?$');
