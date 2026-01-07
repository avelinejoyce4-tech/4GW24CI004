package library;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

public class BookDisplay {

    public static void main(String[] args) {

        try {
            // Step 1: Load Driver
            Class.forName("com.mysql.cj.jdbc.Driver");

            // Step 2: Create Connection
            Connection con = DriverManager.getConnection(
                "jdbc:mysql://localhost:3306/library_db",
                "root",
                "rossy_radha@007"
            );

            // Step 3: Create Statement
            Statement stmt = con.createStatement();

            // Step 4: SQL Query
            String sql = "SELECT * FROM books";

            // Step 5: Execute Query
            ResultSet rs = stmt.executeQuery(sql);

            System.out.println("BOOK ID | TITLE | AUTHOR | ISSUED");
            System.out.println("----------------------------------");

            // Step 6: Read Data
            while (rs.next()) {
                System.out.println(
                        rs.getInt("book_id") + " | " +
                        rs.getString("title") + " | " +
                        rs.getString("author") + " | " +
                        rs.getBoolean("is_issued")
                );
            }
            // Step 7: Close Connection
            con.close();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}

bookdisplay.java