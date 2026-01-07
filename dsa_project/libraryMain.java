package library;

import java.util.Scanner;

public class LibraryMain {

    public static void main(String[] args) {

        Scanner sc = new Scanner(System.in);

        while (true) {
            System.out.println("\n====== DEPARTMENT LIBRARY ======");
            System.out.println("1. Add Book");
            System.out.println("2. Display Books");
            System.out.println("3. Issue Book");
            System.out.println("4. Exit");
            System.out.print("Enter choice: ");

            int choice = sc.nextInt();

            switch (choice) {
                case 1:
                    BookInsert.main(null);
                    break;

                case 2:
                    BookDisplay.main(null);
                    break;

                case 3:
                    IssueBook.main(null);
                    break;

                case 4:
                    System.out.println("Thank you!");
                    System.exit(0);

                default:
                    System.out.println("Invalid choice!");
            }
        }
    }
}