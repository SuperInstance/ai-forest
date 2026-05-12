module arr_mod2
  use iso_c_binding
  implicit none
contains
  subroutine double_arr(arr, n) bind(c, name="double_arr")
    integer(c_int32_t), intent(inout) :: arr(*)
    integer(c_int32_t), intent(in), value :: n
    integer(c_int32_t) :: i
    do i = 1, n
       arr(i) = arr(i) * 2
    end do
  end subroutine
end module
