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

int check_prime(int num){
    int j;
    for(j=1;j<num;++j){
        if(num%j==0){
            break;
        }
    }
    return 1;
}
