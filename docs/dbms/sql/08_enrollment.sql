INSERT INTO ENROLLMENT (STUDENT_ID, COURSE_ID, DIVISION_ID, GROUP_ID)
SELECT
    s.ID,          -- Student's ID
    c.ID,          -- Course ID from the COURSE table
    s.DIVISION_ID, -- Should be 'D3' for these students
    s.GROUP_ID     -- The specific group the student belongs to
FROM
    STUDENT s
CROSS JOIN -- Creates combinations of every D3 student with every course
    COURSE c
WHERE
    s.DIVISION_ID = 'D3';



-- to check enrollment
SELECT COUNT(*)
FROM ENROLLMENT
WHERE STUDENT_ID = :sid AND COURSE_ID = :cid;

SELECT COUNT(*)
FROM ENROLLMENT
WHERE STUDENT_ID = '23bcp153' AND COURSE_ID = '20CP208T';