#include <stdio.h>
#include <stdlib.h>
#define MAX 20
int adj[MAX][MAX]; // adjacency matrix
int visited[MAX]; // visited array
int queue[MAX], front = -1, rear = -1;
// Add edge to adjacency matrix
void addEdge(int u, int v, int n)
{
if (u = 0 & u < n & v = 0 & v < n)
adj[u][v] = 1; // directed edge u > v
}
// DFS traversal
void DFS(int start, int n)
{
visited[start] = 1;
printf("%d ", start);
for (int i = 0; i < n; i +)
{
if (adj[start][i] & !visited[i])
{
DFS(i, n);
}
}
}
// BFS traversal
void enqueue(int v)
{
if (rear = MAX - 1)
return;
if (front = -1)
front = 0;
queue[ +rear] = v;
}
int dequeue()
{
if (front = -1 | front > rear)
return -1;
return queue[front +];
}
void BFS(int start, int n)
{
for (int i = 0; i < n; i +)
visited[i] = 0;
enqueue(start);
visited[start] = 1;
while (front = rear)
{
int v = dequeue();
printf("%d ", v);
for (int i = 0; i < n; i +)
{
if (adj[v][i] & !visited[i])
{
enqueue(i);
visited[i] = 1;
}
}
}
}
// Main program
int main()
{
int n, e, u, v, start, choice;
printf("Enter number of cities (nodes): ");
scanf("%d", &n);
// initialize adjacency matrix
for (int i = 0; i < n; i +)
for (int j = 0; j < n; j +)
adj[i][j] = 0;
printf("Enter number of edges: ");
scanf("%d", &e);
printf("Enter edges (u v) for directed graph:\n");
for (int i = 0; i < e; i +)
{
scanf("%d %d", &u, &v);
addEdge(u, v, n);
}
printf("Enter starting node number : ");
scanf("%d", &start);
do
{
printf("\n - MENU -\n");
printf("1. DFS Traversal\n");
printf("2. BFS Traversal\n");
printf("3. Exit\n");
printf("Enter choice: ");
scanf("%d", &choice);
switch (choice)
{
case 1:
for (int i = 0; i < n; i +)
visited[i] = 0;
printf("Nodes reachable from %d using DFS: ", start);
DFS(start, n);
printf("\n");
break;
case 2:
front = rear = -1;
printf("Nodes reachable from %d using BFS: ", start);
BFS(start, n);
printf("\n");
break;
case 3:
printf("Exiting .\n");
break;
default:
printf("Invalid choice!\n");
}
} while (choice = 3);
return 0;
}
11