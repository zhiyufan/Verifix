/*numPass=0, numTotal=5
Verdict:WRONG_ANSWER, Visibility:1, Input:"5
52 91 72 65 100", ExpOutput:"100 
100 65 
100 65 72 
100 65 72 91 
100 65 72 91 52 
", Output:"
100
10065
1006572
100657291
10065729152"
Verdict:WRONG_ANSWER, Visibility:1, Input:"3
1 22 333", ExpOutput:"333 
333 22 
333 22 1 
", Output:"
333
33322
333221"
Verdict:WRONG_ANSWER, Visibility:1, Input:"10
2346 62 756 452 7274 288 2 81 82 1000", ExpOutput:"1000 
1000 82 
1000 82 81 
1000 82 81 2 
1000 82 81 2 288 
1000 82 81 2 288 7274 
1000 82 81 2 288 7274 452 
1000 82 81 2 288 7274 452 756 
1000 82 81 2 288 7274 452 756 62 
1000 82 81 2 288 7274 452 756 62 2346 
", Output:"
1000
100082
10008281
100082812
100082812288
1000828122887274
1000828122887274452
1000828122887274452756
100082812288727445275662
1000828122887274452756622346"
Verdict:WRONG_ANSWER, Visibility:0, Input:"6 
-2 6 18 27 5 2", ExpOutput:"2 
2 5 
2 5 27 
2 5 27 18 
2 5 27 18 6 
2 5 27 18 6 -2 
", Output:"
2
25
2527
252718
2527186
2527186-2"
Verdict:WRONG_ANSWER, Visibility:0, Input:"8 
-182 571 -27 257 21 9199 -299 12", ExpOutput:"12 
12 -299 
12 -299 9199 
12 -299 9199 21 
12 -299 9199 21 257 
12 -299 9199 21 257 -27 
12 -299 9199 21 257 -27 571 
12 -299 9199 21 257 -27 571 -182 
", Output:"
12
12-299
12-2999199
12-299919921
12-299919921257
12-299919921257-27
12-299919921257-27571
12-299919921257-27571-182"
*/
#include <stdio.h>

int main() {
	int arr[5555],n,i,j,k;
	scanf("%d",&n);
	
	for(i=0;i<=n-1;i++)
	{
	scanf("%d",&arr[i]);
	}
	for(j=0;j<=n-1;j++){
	printf("\n");
	{
    for(k=0;k<=j;k++)
    printf("%d",arr[n-k-1]);
    
	    
	}
	}
	
	
	
	
	
	return 0;
}