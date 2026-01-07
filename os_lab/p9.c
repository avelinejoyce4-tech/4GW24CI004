#include <stdio.h>
#include <stdlib.h>

#define MAX_BLOCKS 100

// Structure to represent a block in the file system
typedef struct Block {
    int blockNumber;
    struct Block* next;
} Block;

// Structure to represent a file
typedef struct File {
    int fileId;
    Block* blocks;
    struct File* next;
} File;

// Global variables
File* files[MAX_BLOCKS] = {NULL}; // Array to hold pointers to file blocks
int lastBlock = 0; // Variable to track the last allocated block

// Function to allocate a block for a file
Block* allocateBlock(int blockNumber) {
    Block* newBlock = (Block*)malloc(sizeof(Block));
    if (newBlock == NULL) {
        printf("Memory allocation failed\n");
        exit(1);
    }
    newBlock->blockNumber = blockNumber;
    newBlock->next = NULL;
    return newBlock;
}

// Function to create a new file
void createFile(int fileId) {
    File* newFile = (File*)malloc(sizeof(File));
    if (newFile == NULL) {
        printf("Memory allocation failed\n");
        exit(1);
    }
    newFile->fileId = fileId;
    newFile->blocks = NULL;
    newFile->next = NULL;
    
    // Insert the file into the files array
    files[fileId] = newFile;
    printf("File created with ID %d\n", fileId);
}

// Function to allocate blocks for a file
void allocateBlocks(int fileId, int numBlocks) {
    File* file = files[fileId];
    if (file == NULL) {
        printf("File with ID %d does not exist\n", fileId);
        return;
    }
    
    // Allocate blocks for the file
    int i;
    for (i = 0; i < numBlocks; i++) {
        Block* newBlock = allocateBlock(++lastBlock);
        newBlock->next = file->blocks;
        file->blocks = newBlock;
    }
    printf("%d blocks allocated for file %d\n", numBlocks, fileId);
}

// Function to delete a file
void deleteFile(int fileId) {
    File* file = files[fileId];
    if (file == NULL) {
        printf("File with ID %d does not exist\n", fileId);
        return;
    }
    
    // Free blocks allocated to the file
    Block* current = file->blocks;
    while (current != NULL) {
        Block* temp = current;
        current = current->next;
        free(temp);
    }
    
    // Free file structure
    free(file);
    files[fileId] = NULL;
    printf("File with ID %d deleted\n", fileId);
}

// Function to display allocated blocks for a file
void displayFile(int fileId) {
    File* file = files[fileId];
    if (file == NULL) {
        printf("File with ID %d does not exist\n", fileId);
        return;
    }
    
    printf("Blocks allocated for file %d: ", fileId);
    Block* current = file->blocks;
    while (current != NULL) {
        printf("%d ", current->blockNumber);
        current = current->next;
    }
    printf("\n");
}

int main() {
    int choice, fileId, numBlocks;
    
    while (1) {
        printf("\nLinked File Allocation Strategies\n");
        printf("1. Create File\n");
        printf("2. Allocate Blocks\n");
        printf("3. Delete File\n");
        printf("4. Display File\n");
        printf("5. Exit\n");
        printf("Enter your choice: ");
        scanf("%d", &choice);
        
        switch (choice) {
            case 1:
                printf("Enter file ID: ");
                scanf("%d", &fileId);
                createFile(fileId);
                break;
            case 2:
                printf("Enter file ID: ");
                scanf("%d", &fileId);
                printf("Enter number of blocks: ");
                scanf("%d", &numBlocks);
                allocateBlocks(fileId, numBlocks);
                break;
            case 3:
                printf("Enter file ID to delete: ");
                scanf("%d", &fileId);
                deleteFile(fileId);
                break;
            case 4:
                printf("Enter file ID to display: ");
                scanf("%d", &fileId);
                displayFile(fileId);
                break;
            case 5:
                exit(0);
            default:
                printf("Invalid choice\n");
        }
    }
    
    return 0;
}

