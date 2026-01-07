#include<stdlib.h>
#include<stdio.h>
#include<string.h>
void readstring (char str[],size_t maxlen,const char*label)
{
    int c;
    printf("Enter %s",label);
    if(fgets(str,(int)maxlen,stdin)==NULL)
  { 
    str[0]='\0';
    return;
  }
  size_t len=strlen(str);
  if(len>0 && str[len-1]=='\n')
  {
     str[len-1]='\0';
  }
  else{
      while((c=getchar())!= '\n' && c!=EOF)
    {
        {

         }   
    } 
  }
}
 int stringLength(char str[])
   {
     int len=0;
     while(str[len]!= '\0')
     len++;
   return len;
    }
   int isMatch (char str[],char pat[],int pos)
  {
     int i=0;
     while(pat[i]!='\0')
     {
         if(str[pos+i]!=pat[i])
         return 0;
    i++;
      }
     return 1;
   }
    void replacePattern (char str[],char pat[],char rep[], char result[])
    {
    int i=0,j=0;
    int found=1;
    int lenSTR=stringLength(str);
    int lenPAT=stringLength(pat);
    int lenREP=stringLength(rep);
    while(i<lenSTR)
    {
           if(isMatch(str, pat, i))
            {
            found=1;
               for(int k=0;k<lenREP;k++ )
                {
                 result[j++]=rep[k];
                 }
                 i +=lenPAT;
             }
            else
            {  
              result[j++] = str[i++];
             }   

    }
 result[j] = '\0';

 if(found)
     printf("\n Updated string %s\n", result);
 else
     printf("\n Pattern not found in main String\n");
    }

int main()
{
char STR[100],PAT[50],REP[50],RESULT[200];
readstring(STR,sizeof STR,"Main String(STR)");
readstring(PAT,sizeof PAT,"Pattern STring(PAT)");
readstring(REP,sizeof REP,"Replace String (REP)");
replacePattern(STR,PAT,REP,RESULT);
return 0;

}