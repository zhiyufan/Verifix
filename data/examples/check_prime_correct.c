#include<stdio.h>
int check_prime(int num);
int main(){
   int n1,n2,i,flag;
   scanf("%d %d",&n1, &n2);
   for(i=n1;i<=n2;++i){
      flag=check_prime(i);
      if(flag==1)
         printf("%d ",i);
   }
   return 0;
}

int check_prime(int n){
    if (n==1)
        return 0;
    int j;
    for(j=2; j<n;j++){
        if (n%j==0)
            return 0;
    }
    return 1;
}
