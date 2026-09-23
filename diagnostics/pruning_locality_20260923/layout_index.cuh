#pragma once

// Fixed H3 screen: root plus ten child-parent pivots. No production dispatcher.
__host__ __device__ __forceinline__ int pivotOffset(int kind,int group,int j,int dim) {
    if(kind==1)return j*16+group;
    if(kind==2)return group*dim+j;
    if(group==0)return j;
    int blocks=(dim+7)/8,p=group-1;
    return blocks*8+((p/4)*blocks+j/8)*32+(p%4)*8+j%8;
}
__host__ __device__ __forceinline__ int pivotWords(int kind,int dim) {
    if(kind==1)return 16*dim;
    if(kind==2)return 11*dim;
    return ((dim+7)/8)*104;
}
