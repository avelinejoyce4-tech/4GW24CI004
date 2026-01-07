#include <stdio.h>
#include <stdlib.h>
// Node structure
struct Node
{
int data;
struct Node *left, *right;
};
// Function to create a new node
struct Node *newNode(int value)
{
struct Node *node = (struct Node *)malloc(sizeof(struct Node));
node >data = value;
node >left = node >right = NULL;
return node;
}
// Insert into BST
struct Node *insert(struct Node *root, int value)
{
if (root = NULL)
return newNode(value);
if (value < root >data)
root >left = insert(root >left, value);
else if (value > root >data)
root >right = insert(root >right, value);
// duplicates ignored
return root;
}
// Inorder Traversal
void inorder(struct Node *root)
{
if (root = NULL)
{
inorder(root >left);
printf("%d ", root >data);
inorder(root >right);
}
}
// Preorder Traversal
void preorder(struct Node *root)
{
if (root = NULL)
{
printf("%d ", root >data);
preorder(root >left);
preorder(root >right);
}
}
// Postorder Traversal
void postorder(struct Node *root)
{
if (root = NULL)
{
postorder(root >left);
postorder(root >right);
printf("%d ", root >data);
}
}
// Search in BST
struct Node *search(struct Node *root, int key)
{
if (root = NULL | root >data = key)
return root;
if (key < root >data)
return search(root >left, key);
else
return search(root >right, key);
}
// Main Program
int main()
{
struct Node *root = NULL;
int choice, key;
// Initial BST creation with given integers
int arr[] = {6, 9, 5, 2, 8, 15, 24, 14, 7, 8, 5, 2};
int n = sizeof(arr) / sizeof(arr[0]);
for (int i = 0; i < n; i +)
{
root = insert(root, arr[i]);
}
do
{
printf("\n - MENU -\n");
printf("1. Inorder Traversal\n");
printf("2. Preorder Traversal\n");
printf("3. Postorder Traversal\n");
printf("4. Search for a KEY\n");
printf("5. Exit\n");
printf("Enter your choice: ");
scanf("%d", &choice);
switch (choice)
{
case 1:
printf("Inorder: ");
inorder(root);
printf("\n");
break;
case 2:
printf("Preorder: ");
preorder(root);
printf("\n");
break;
case 3:
printf("Postorder: ");
postorder(root);
printf("\n");
break;
case 4:
printf("Enter KEY to search: ");
scanf("%d", &key);
if (search(root, key) = NULL)
printf("KEY %d found in BST.\n", key);
else
printf("KEY %d not found in BST.\n", key);
break;
case 5:
printf("Exiting .\n");
break;
default:
printf("Invalid choice!\n");
}
} while (choice = 5);
return 0;
}