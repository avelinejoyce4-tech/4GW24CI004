package library;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;

public class IssueBook {

    public static void main(String[] args) {

        try {
            Class.forName("com.mysql.cj.jdbc.Driver");

            Connection con = DriverManager.getConnection(
                "jdbc:mysql://localhost:3306/library_db",
                "root",
                "rossy_radha@007"
            );

            // Step 1: Insert into issued_books
            String sql = "INSERT INTO issued_books (book_id, student_id, issue_date) VALUES (?, ?, CURDATE())";
            PreparedStatement ps = con.prepareStatement(sql);
            ps.setInt(1, 101);
            ps.setInt(2, 1);

            int rows = ps.executeUpdate();
            System.out.println("Rows inserted into issued_books: " + rows);

            // Step 2: Update books table to mark as issued
            String updateBook = "UPDATE books SET is_issued = 1 WHERE book_id = ?";
            PreparedStatement ps2 = con.prepareStatement(updateBook);
            ps2.setInt(1, 101);

            int updatedRows = ps2.executeUpdate();
            if (updatedRows > 0) {
                System.out.println("Book status updated to issued in books table");
            } else {
                System.out.println("Failed to update book status, book not found");
            }

            con.close();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}