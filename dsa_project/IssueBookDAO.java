package library;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.util.Scanner;

public class IssueBookDAO {

    public static void issueBook() {

        Scanner sc = new Scanner(System.in);

        System.out.print("Enter Book ID: ");
        int bookId = sc.nextInt();

        System.out.print("Enter Student ID: ");
        int studentId = sc.nextInt();

        try {
            Connection con = DBConnection.getConnection();

            String sql = "INSERT INTO issued_books (book_id, student_id, issue_date) VALUES (?, ?, CURDATE())";

            PreparedStatement ps = con.prepareStatement(sql);
            ps.setInt(1, bookId);
            ps.setInt(2, studentId);

            int rows = ps.executeUpdate();

            if (rows > 0) {
                System.out.println("Book Issued Successfully ✅");
            } else {
                System.out.println("Issue Failed ❌");
            }

            con.close();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}