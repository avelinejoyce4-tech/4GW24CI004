package library;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;

public class BookInsert {

    public static void main(String[] args) {

        try {
            Connection con = DriverManager.getConnection(
                "jdbc:mysql://localhost:3306/library_db",
                "root",
                "rossy_radha@007"
            );

            int bookId = 101;   // ✅ DECLARED HERE

            // Step 1: Check if book exists
            String checkSql = "SELECT * FROM books WHERE book_id = ?";
            PreparedStatement checkPs = con.prepareStatement(checkSql);
            checkPs.setInt(1, bookId);

            ResultSet rs = checkPs.executeQuery();

            if (rs.next()) {
                System.out.println("Book already exists!");
                con.close();
                return;
            }

            // Step 2: Insert book
            String sql = "INSERT INTO books VALUES (?, ?, ?, ?)";
            PreparedStatement ps = con.prepareStatement(sql);

            ps.setInt(1, bookId);
            ps.setString(2, "Data Structures");
            ps.setString(3, "Mark Allen");
            ps.setBoolean(4, false);

            int rows = ps.executeUpdate();
            System.out.println("Book inserted successfully");

            con.close();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}