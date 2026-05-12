module arr_mod
  use iso_c_binding
  implicit none
contains
  subroutine double_arr(ptr, n) bind(c, name="double_arr")
    type(c_ptr), value :: ptr
    integer(c_int32_t), intent(in) :: n
    integer(c_int32_t), pointer :: arr(:)
    integer(c_int32_t) :: i
    call c_f_pointer(ptr, arr, [n])
    do i = 1, n
       arr(i) = arr(i) * 2
    end do
  end subroutine
end module
