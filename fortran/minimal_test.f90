! Minimal Fortran claw — use c_ptr for raw array access
module minimal_claw
  use, intrinsic :: iso_c_binding
  implicit none
contains
  subroutine double_values(arr_ptr, n) bind(c, name="double_values")
    type(c_ptr), value :: arr_ptr
    integer(c_int32_t), intent(in) :: n
    integer(c_int32_t), pointer :: arr(:)
    integer(c_int32_t) :: i

    call c_f_pointer(arr_ptr, arr, [n])
    do i = 1, n
       arr(i) = arr(i) * 2
    end do
  end subroutine double_values
end module minimal_claw
