! Compiled from: compute_chain.flx
! FLUX → Fortran Compiler
! Generates direct Fortran .so calls for all extension opcodes

program flux_program
  use, intrinsic :: iso_c_binding
  implicit none
  integer(c_int32_t) :: i, nr, n
  integer(c_int32_t), allocatable :: a(:), b(:), r(:)

  ! Ignored: LDA room_a        ; load room a address
  ! Ignored: LDB room_b        ; load room b address
  call contract(a, size(a), b, size(b), ;, nr)
  call gradient(a, size(a), r)
  ! Ignored: MOV r2, r0        ; copy to result
  ! Ignored: PLATO_WRITE synthesis, "Compute chain complete"
  ! Ignored: HALT
end program flux_program