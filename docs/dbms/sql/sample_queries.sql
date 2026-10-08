-- Get Attendance List for a Specific Course on a Specific Date:

SELECT
    s.ID AS StudentID,
    s.NAME AS StudentName,
    a.STATUS AS AttendanceStatus
FROM
    ATTENDANCE a
JOIN
    STUDENT s ON a.STUDENT_ID = s.ID
WHERE
    a.COURSE_ID = '20CP208P'  -- Replace with the actual Course ID
    AND a.DATE = '2024-03-10'; -- Replace with the actual Date
ORDER BY
    s.NAME;



-- Get a Specific Student's Attendance Record for a Specific Course:

SELECT
    a.DATE,
    a.STATUS
FROM
    ATTENDANCE a
WHERE
    a.STUDENT_ID = '23BCP153' -- Replace with the actual Student ID
    AND a.COURSE_ID = '20CP208P' -- Replace with the actual Course ID
ORDER BY
    a.DATE DESC;



-- List Students Who Were Absent for a Specific Course on a Specific Date:

SELECT
    s.ID AS StudentID,
    s.NAME AS StudentName
FROM
    STUDENT s
JOIN
    ENROLLMENT e ON s.ID = e.STUDENT_ID
WHERE
    e.COURSE_ID = '20CP208P' -- Replace with the actual Course ID
    AND s.ID NOT IN (
        SELECT DISTINCT STUDENT_ID
        FROM ATTENDANCE
        WHERE COURSE_ID = '20CP208P' -- Replace with the actual Course ID
          AND DATE = '2024-03-10'   -- Replace with the actual Date
          AND STATUS = 'Present'     -- Assuming only 'Present' is marked reliably
    )
ORDER BY
    s.NAME;

-- Alternative using LEFT JOIN (can be more efficient on some DBs)
-- SELECT
--     s.ID AS StudentID,
--     s.NAME AS StudentName
-- FROM
--     STUDENT s
-- JOIN
--     ENROLLMENT e ON s.ID = e.STUDENT_ID
-- LEFT JOIN
--     ATTENDANCE a ON s.ID = a.STUDENT_ID
--                  AND a.COURSE_ID = e.COURSE_ID
--                  AND a.DATE = '2024-03-10' -- Replace with the actual Date
--                  AND a.STATUS = 'Present'
-- WHERE
--     e.COURSE_ID = '20CP208P' -- Replace with the actual Course ID
--     AND a.STUDENT_ID IS NULL -- This means no matching 'Present' attendance record was found
-- ORDER BY
--     s.NAME;


-- Get Attendance Summary (Count) for Each Student in a Specific Course:
SELECT
    s.ID AS StudentID,
    s.NAME AS StudentName,
    COUNT(a.DATE) AS DaysPresent -- Counts non-null dates where student was present
FROM
    STUDENT s
JOIN
    ENROLLMENT e ON s.ID = e.STUDENT_ID
LEFT JOIN -- Use LEFT JOIN to include enrolled students even if they have 0 attendance
    ATTENDANCE a ON s.ID = a.STUDENT_ID
                 AND e.COURSE_ID = a.COURSE_ID
                 AND a.STATUS = 'Present'
    -- Optional: Add date range condition here if needed
    -- AND a.DATE BETWEEN '2024-02-01' AND '2024-03-10'
WHERE
    e.COURSE_ID = '20CP208P' -- Replace with the actual Course ID
GROUP BY
    s.ID, s.NAME
ORDER BY
    s.NAME;


-- Get Total Attendance Count Per Day for a Specific Course:

SELECT
    DATE,
    COUNT(STUDENT_ID) AS StudentsPresent
FROM
    ATTENDANCE
WHERE
    COURSE_ID = '20CP208P' -- Replace with the actual Course ID
    AND STATUS = 'Present'
GROUP BY
    DATE
ORDER BY
    DATE DESC;


-- Find Courses a Specific Student is Enrolled In:
SELECT
    c.ID AS CourseID,
    c.COURSE_NAME AS CourseName
FROM
    COURSE c
JOIN
    ENROLLMENT e ON c.ID = e.COURSE_ID
WHERE
    e.STUDENT_ID = '23BCP153' -- Replace with the actual Student ID
ORDER BY
    c.ID;


