#include <stdio.h>
int main(){
  int a, b, c = 0;
  scanf("%d %d", &a, &b);
  c=a*a + b*b;
  printf("Sum of square of %d and square of %d is %d.", a, b, c);
  return 0;
}
