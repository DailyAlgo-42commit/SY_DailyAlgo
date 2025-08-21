//문자열 반복해서 출력하기
#include <iostream>
#include <string>

using namespace std;

int main(void) {
    string str;
    int n;
    cin >> str >> n;
    
    for(int i=1; i<=n; i++){
        cout << str;
    }
    return 0;
}