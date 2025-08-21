//1부터의 합
#include <iostream>
using namespace std;

int main() {
    int n;
    int sum=0;
    cin >> n;

    for(int i=1; i<=100; i++)
    {
        sum+=i;
        if(sum>=n)
        {
            cout << i << "\n";
            break;
        }
    }
    return 0;
}