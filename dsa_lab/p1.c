#include<stdio.h>
#include<stdlib.h>
struct Day
{
    char *dayName;
    char *activity;
    int date;
};

void create(struct Day *day)
{
    day->dayName=(char*)malloc(sizeof(char)*20);
    day->activity=(char*)malloc(sizeof(char)*100);
    printf("enter the dayname");
    scanf("%s", day->dayName);
    printf("enter the date");
    scanf("%d", &day->date);
    printf("enter the activity for the day");
    scanf("%s", day->activity);
}
void read(struct Day *calendar, int size)
{
    for(int i=0; i<size; i++)
    {
        printf("enter the details for the day %d:\n", i+1);
        create(&calendar[i]);
    }
}
void display(struct Day *calendar, int size)
{
    printf("week's activity details\n");
    for(int i=0; i<size; i++)
    {
        printf("day %d:\n", i+1);
        printf("dayname:%s\n", calendar[i].dayName);
        printf("date:%d",calendar[i].date);
        printf("activity: %s\n",calendar[i].activity);
        printf("\n");
    }
}
void freeMemory(struct Day *calendar, int size)
{
    for(int i=0; i<size; i++)
    {
        free(calendar[i].dayName);
        free(calendar[i].activity);
    }
}
int main()
{
    int size;
    printf("enter the number of days in week:");
    scanf("%d", &size);
    struct Day *calendar=(struct Day *)malloc(sizeof(struct Day)*size);
    if (calendar==NULL)
    {
        printf("\n Memory Allocation failed. Exiting program");
        return 1;
    }
    read(calendar, size);
    display(calendar, size);
    freeMemory(calendar, size);
    free(calendar);
    return 0;
}